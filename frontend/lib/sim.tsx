"use client";

import { useSearchParams } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { API_URL, api, type SimEvent, type SimState } from "./api";
import { dayLabel } from "./format";

const FEED_MAX = 300;

// Used until the backend answers (or if it's offline) so the shell never breaks.
const OFFLINE_STATE: SimState = {
  run_id: null,
  seed: 42,
  scenario: "typical",
  autopilot: false,
  day: 0,
  day_label: dayLabel(0),
  stage: "NUDGE",
  status_text: "Ready to send the nudge",
  waiting_for_approval: false,
  pending_rows: 0,
  counters: { sent: 0, replied: 0, flagged: 0, joined: 0, follow_ups: 0, beat_prediction: 0 },
  playing: false,
  speed_seconds_per_day: 2,
  steps: [
    { key: "nudge", label: "Cohorts + survey", day: 0, day_label: dayLabel(0) },
    { key: "plan", label: "Next best actions", day: 7, day_label: dayLabel(7) },
    { key: "send", label: "Actions sent", day: 8, day_label: dayLabel(8) },
    { key: "results", label: "Results + refresh", day: 30, day_label: dayLabel(30) },
  ],
};

type SimContextValue = {
  state: SimState;
  online: boolean;
  feed: SimEvent[];          // newest first
  apply: (s: SimState) => void;
  refresh: () => void;
};

const SimContext = createContext<SimContextValue>({
  state: OFFLINE_STATE,
  online: false,
  feed: [],
  apply: () => {},
  refresh: () => {},
});

function merge(feed: SimEvent[], incoming: SimEvent[]): SimEvent[] {
  const seen = new Set(feed.map((e) => e.event_id));
  const fresh = incoming.filter((e) => !seen.has(e.event_id));
  if (!fresh.length) return feed;
  return [...fresh, ...feed]
    .sort((a, b) => b.sim_day - a.sim_day || b.event_id - a.event_id)
    .slice(0, FEED_MAX);
}

export function SimProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SimState>(OFFLINE_STATE);
  const [online, setOnline] = useState(false);
  const [feed, setFeed] = useState<SimEvent[]>([]);

  // A new run's feed is cleared by the stream's `reset` event.
  const apply = useCallback((s: SimState) => {
    setState(s);
    setOnline(true);
  }, []);

  const refresh = useCallback(() => {
    api.simState().then(apply).catch(() => setOnline(false));
  }, [apply]);

  // Live: the server streams state changes and newly visible events. EventSource reconnects on its own;
  // a slow poll covers the gap if the stream is down.
  useEffect(() => {
    const es = new EventSource(`${API_URL}/sim/stream`);
    es.addEventListener("state", (e) => apply(JSON.parse((e as MessageEvent).data)));
    es.addEventListener("events", (e) => setFeed((f) => merge(f, JSON.parse((e as MessageEvent).data))));
    es.addEventListener("reset", () => setFeed([]));
    es.onerror = () => setOnline(false);
    const poll = setInterval(() => {
      if (es.readyState !== EventSource.OPEN) refresh();
    }, 5000);
    return () => {
      es.close();
      clearInterval(poll);
    };
  }, [apply, refresh]);

  return <SimContext.Provider value={{ state, online, feed, apply, refresh }}>{children}</SimContext.Provider>;
}

export function useSim() {
  return useContext(SimContext);
}

/** The day a page should show: `?day=` if present (clamped to the live day), else the live day. */
export function useViewDay(): { day: number; live: boolean } {
  const { state } = useSim();
  const raw = useSearchParams().get("day");
  const asked = raw === null ? NaN : Number(raw);
  if (Number.isFinite(asked) && asked < state.day) return { day: Math.max(0, asked), live: false };
  return { day: state.day, live: true };
}
