"use client";

import { useEffect, useEffectEvent, useState } from "react";

type Result<T> = { key: string; data?: T; error?: string };

/**
 * Fetch when `key` changes (null = skip). Keeps the previous data on screen while the next request loads,
 * so cards change smoothly instead of flashing empty.
 */
export function useApi<T>(key: string | null, fetcher: () => Promise<T>) {
  const [res, setRes] = useState<Result<T>>();
  const [last, setLast] = useState<T>();
  const run = useEffectEvent(() => fetcher());

  useEffect(() => {
    if (key === null) return;
    let alive = true;
    run()
      .then((data) => {
        if (!alive) return;
        setRes({ key, data });
        setLast(data);
      })
      .catch((e: unknown) => alive && setRes({ key, error: e instanceof Error ? e.message : String(e) }));
    return () => {
      alive = false;
    };
  }, [key]);

  const current = res?.key === key ? res : undefined;
  return { data: current?.data ?? last, loading: !current, error: current?.error };
}
