"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArrowRight, BotMessageSquare, Flag, MessageCircle, Phone as PhoneIcon } from "lucide-react";
import { api, type ChatView, type JourneyItem } from "@/lib/api";
import { useSim, useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";
import { PageHeader } from "@/components/shell/PageHeader";
import { Phone } from "./Phone";

const ICON = { bengali: MessageCircle, flag: Flag, call: PhoneIcon } as const;
const AGENT_TONE: Record<string, string> = {
  "Nudge agent": "bg-blue-soft text-emami-blue",
  "Survey agent": "bg-blue-soft text-emami-blue",
  "CTA agent": "bg-orange-soft text-amber",
  You: "bg-navy-800 text-white",
  Autopilot: "bg-navy-800 text-white",
  Execution: "bg-green-soft text-green-text",
  "Results agent": "bg-green-soft text-green-text",
  Persona: "bg-[#EEF1F5] text-ink",
};

export function DistributorView() {
  const { day, live } = useViewDay();
  const { state } = useSim();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const id = params.get("id") ?? "DST-0001";
  const [version, setVersion] = useState(0);
  const [sent, setSent] = useState<ChatView | null>(null);

  const scenarios = useApi(`scen:${day.toFixed(2)}`, () => api.scenarios(day));
  const everyone = useApi("all-distributors", () => api.distributors("", 0));
  const chat = useApi(`chat:${id}:${day.toFixed(2)}:${version}`, () => api.chat(id, day));
  const data = sent && sent.distributor_id === id && chat.data && chat.data.messages.length < sent.messages.length ? sent : chat.data;

  function open(next: string) {
    const p = new URLSearchParams(params.toString());
    p.set("id", next);
    setSent(null);
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  }

  async function send(text: string) {
    const v = await api.chatSend(id, text);
    setSent(v);
    setVersion((x) => x + 1);
  }

  return (
    <>
      <PageHeader eyebrow="Distributor view" badge="Simulated WhatsApp · Festive Scheme loop" title="What the distributor sees, start to finish" />
      <div className="grid items-start gap-5 lg:grid-cols-[260px_1fr] xl:grid-cols-[260px_1fr_330px]">
        <div className="space-y-5">
          <Card className="p-5">
            <p className="text-[13px] font-semibold uppercase tracking-[0.1em] text-muted">Play a scenario</p>
            <div className="mt-3 space-y-2.5">
              {(scenarios.data ?? []).map((s) => {
                const active = s.distributor_id === id;
                const Icon = ICON[s.icon];
                return (
                  <motion.button
                    key={s.distributor_id}
                    type="button"
                    onClick={() => open(s.distributor_id)}
                    whileTap={{ scale: 0.98 }}
                    aria-pressed={active}
                    className={`relative flex w-full items-start gap-3 rounded-2xl border p-3.5 text-left transition-colors ${
                      active ? "border-transparent text-white" : "border-card-border text-ink hover:bg-bg"
                    }`}
                  >
                    {active && <motion.span layoutId="scenario-active" className="absolute inset-0 rounded-2xl bg-navy-800" transition={{ duration: 0.35, ease: EASE }} />}
                    <span className={`relative grid size-10 shrink-0 place-items-center rounded-xl ${active ? "bg-orange text-ink" : "bg-blue-soft text-emami-blue"}`}>
                      <Icon className="size-5" aria-hidden />
                    </span>
                    <span className="relative min-w-0">
                      <span className="block text-[15px] font-semibold">{s.title}</span>
                      <span className={`block text-[13px] leading-snug ${active ? "text-white/80" : "text-muted"}`}>{s.subtitle}</span>
                    </span>
                  </motion.button>
                );
              })}
            </div>
            <label className="mt-4 block text-[13px] text-muted">
              Or open any distributor
              <select
                value={id}
                onChange={(e) => open(e.target.value)}
                className="mt-1 min-h-11 w-full rounded-xl border border-card-border bg-white px-3 text-[14px] text-ink"
              >
                {(everyone.data?.items ?? []).map((d) => (
                  <option key={d.distributor_id} value={d.distributor_id}>
                    {d.name} · {d.town}
                  </option>
                ))}
              </select>
            </label>
          </Card>
          {data && <Profile d={data} />}
        </div>

        <Phone data={data} canType={live && state.day >= 0.42} onSend={send} />

        <div className="lg:col-span-2 xl:col-span-1">
          <Behind items={data?.journey ?? []} />
        </div>
      </div>
    </>
  );
}

function Profile({ d }: { d: ChatView }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-navy-800 font-display text-[17px] font-semibold text-orange-light">{d.initials}</span>
        <div className="min-w-0">
          <p className="text-[16px] font-semibold leading-snug text-ink">{d.name}</p>
          <p className="truncate text-[13px] text-muted">
            {d.owner_name} · {d.town}
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-full bg-orange-soft px-2.5 py-1 text-[13px] font-medium text-amber">{d.cohort}</span>
        <span className="rounded-full bg-[#EEF1F5] px-2.5 py-1 text-[13px] font-medium text-ink">
          Prefers {d.language}
          {d.language_changed && " · learned"}
        </span>
      </div>
      <dl className="mt-3 divide-y divide-card-border text-[14px]">
        <Row k="Billing FYTD" v={d.billing_fytd} />
        <Row k="Best time to message" v={d.best_time} />
        <Row k="This cycle" v={d.this_cycle} />
      </dl>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 py-2.5">
      <dt className="text-muted">{k}</dt>
      <dd className="whitespace-nowrap text-right font-semibold text-ink">{v}</dd>
    </div>
  );
}

function Behind({ items }: { items: JourneyItem[] }) {
  return (
    <Card className="flex flex-col p-6 xl:min-h-[640px]">
      <p className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.1em] text-amber">
        <BotMessageSquare className="size-4" aria-hidden /> Behind the conversation
      </p>
      <h2 className="mt-1 font-display text-[22px] font-semibold text-ink">What the agents did</h2>
      <ol className="relative mt-4 flex-1">
        {items.length === 0 && <li className="text-[14px] text-muted">Nothing yet — the agents start at Day 0 10:00.</li>}
        {items.map((j, i) => (
          <motion.li
            key={`${j.sim_day}:${i}`}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, ease: EASE, delay: Math.min(i, 10) * 0.04 }}
            className="relative pb-5 pl-7 last:pb-0"
          >
            {i < items.length - 1 && <span className="absolute left-[5px] top-4 h-full w-px bg-card-border" aria-hidden />}
            <span
              className={`absolute left-0 top-1.5 size-[11px] rounded-full ${i === items.length - 1 ? "bg-orange" : "bg-emami-blue"}`}
              aria-hidden
            />
            <p className="flex flex-wrap items-center gap-2 text-[13px] text-muted">
              {j.day_label} · {j.time_label}
              <span className={`rounded-full px-2 py-0.5 text-[12px] font-medium ${AGENT_TONE[j.agent] ?? AGENT_TONE.Persona}`}>{j.agent}</span>
            </p>
            <p className="mt-0.5 text-[15px] leading-snug text-ink">{j.text}</p>
          </motion.li>
        ))}
      </ol>
      <Link
        href="/approvals"
        className="mt-5 flex min-h-12 items-center justify-center gap-2 rounded-xl bg-bg text-[15px] font-semibold text-emami-blue hover:bg-blue-soft"
      >
        Back to approvals <ArrowRight className="size-4" aria-hidden />
      </Link>
    </Card>
  );
}
