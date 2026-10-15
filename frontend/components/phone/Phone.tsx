"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { BadgeCheck, ChevronLeft, Phone as PhoneIcon, SendHorizontal, Smile } from "lucide-react";
import type { ChatView } from "@/lib/api";
import { possessive } from "@/lib/format";
import { Bubble, Typing } from "./Bubbles";

function dateChip(dayLabel: string): string {
  const [d, date] = dayLabel.split(" · ");
  return `${date} · ${d}`;
}

/** Simulated WhatsApp on the distributor's phone. The input box lets the presenter type as the distributor. */
export function Phone({
  data,
  canType,
  onSend,
}: {
  data: ChatView | undefined;
  canType: boolean;
  onSend: (text: string) => Promise<void>;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const count = data?.messages.length ?? 0;

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [count, sending, data?.distributor_id]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t || sending) return;
    setSending(true);
    setText("");
    try {
      await onSend(t);
    } finally {
      setSending(false);
    }
  }

  let last = "";
  return (
    <section className="rounded-[24px] bg-navy-800 px-4 pb-5 pt-5 sm:px-8">
      <p className="flex items-center justify-center gap-2 text-[14px] text-white/85">
        <span className="size-2 rounded-full bg-[#25D366]" aria-hidden />
        Live preview · {data ? `${possessive(data.name)} phone` : "loading"}
      </p>
      <div className="mx-auto mt-4 w-full max-w-[350px] rounded-[46px] border-[10px] border-[#11161C] bg-[#11161C] shadow-[0_20px_50px_-20px_rgba(0,0,0,0.6)]">
        <div className="relative overflow-hidden rounded-[36px] bg-[#EFE7DD]">
          <div className="absolute left-1/2 top-2 z-10 h-6 w-24 -translate-x-1/2 rounded-full bg-[#11161C]" aria-hidden />
          {/* WhatsApp header */}
          <div className="flex items-center gap-2.5 bg-navy-800 px-3 pb-3 pt-10 text-white">
            <ChevronLeft className="size-5 shrink-0" aria-hidden />
            <span className="grid size-9 shrink-0 place-items-center overflow-hidden rounded-full bg-white">
              <Image src="/brand/emami-logo.png" alt="" width={30} height={27} />
            </span>
            <span className="min-w-0 flex-1 leading-tight">
              <span className="flex items-center gap-1 text-[15px] font-semibold">
                Emami Distributor Desk <BadgeCheck className="size-4 text-[#25D366]" aria-label="verified business" />
              </span>
              <span className="block text-[12px] text-white/70">Business account · online</span>
            </span>
            <PhoneIcon className="size-5 shrink-0" aria-hidden />
          </div>
          {/* Chat */}
          <div ref={scroller} className="h-[460px] overflow-y-auto px-3 py-2" aria-live="polite">
            {data && data.messages.length === 0 && (
              <p className="mt-24 text-center text-[13px] text-[#54656F]">No messages yet. The nudge goes out on Day 0 at 10:00.</p>
            )}
            {data?.messages.map((m) => {
              const chip = m.day_label !== last ? dateChip(m.day_label) : null;
              last = m.day_label;
              return (
                <div key={`${data.distributor_id}:${m.id}`}>
                  {chip && (
                    <div className="my-2 flex justify-center">
                      <span className="rounded-lg bg-white px-2.5 py-1 text-[12px] font-medium text-[#54656F] shadow-sm">{chip}</span>
                    </div>
                  )}
                  <Bubble m={m} />
                </div>
              );
            })}
            {sending && <Typing />}
          </div>
          {/* Composer */}
          <form onSubmit={send} className="flex items-center gap-2 bg-[#EFE7DD] px-2.5 pb-4 pt-1.5">
            <label className="flex min-h-11 flex-1 items-center gap-2 rounded-full bg-white px-3.5 shadow-sm">
              <Smile className="size-5 shrink-0 text-[#8696A0]" aria-hidden />
              <span className="sr-only">Type as distributor</span>
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={!canType || sending}
                placeholder={canType ? "Type as distributor…" : "Opens after the Day-0 nudge"}
                className="min-w-0 flex-1 bg-transparent text-[14px] text-[#111B21] outline-none placeholder:text-[#8696A0]"
              />
            </label>
            <button
              type="submit"
              disabled={!canType || sending || !text.trim()}
              aria-label="Send"
              className="grid size-11 shrink-0 place-items-center rounded-full bg-emami-blue text-white transition-opacity disabled:opacity-50"
            >
              <SendHorizontal className="size-5" aria-hidden />
            </button>
          </form>
        </div>
      </div>
      <p className="mt-4 text-center text-[13px] text-white/70">Scroll inside the phone to read the full conversation · type to reply as the distributor</p>
    </section>
  );
}
