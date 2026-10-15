"use client";

import { motion } from "motion/react";
import { CheckCheck, CircleCheck, Phone, Play } from "lucide-react";
import type { Message } from "@/lib/api";
import { EASE } from "@/components/motion/Motion";

const langAttr = (l?: string | null) => (l === "Bengali" ? "bn" : l === "Hindi" ? "hi" : undefined);

function Meta({ m, mine }: { m: Message; mine: boolean }) {
  return (
    <span className="mt-1 flex items-center justify-end gap-1 text-[11px] text-[#667781]">
      {m.time_label}
      {mine && <CheckCheck className="size-3.5 text-[#53BDEB]" aria-label="read" />}
    </span>
  );
}

export function Bubble({ m }: { m: Message }) {
  const mine = m.sender === "distributor";
  if (m.kind === "call")
    return (
      <div className="my-2 flex justify-center">
        <span className="flex items-center gap-2 rounded-lg bg-white/90 px-3 py-1.5 text-[12px] text-[#54656F] shadow-sm">
          <Phone className="size-3.5 text-green-text" aria-hidden />
          {m.text} · {m.time_label}
        </span>
      </div>
    );

  if (m.kind === "quick_replies")
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: EASE }} className="my-1.5 max-w-[88%]">
        <div className="rounded-xl rounded-tl-sm bg-white px-3 py-2 text-[14px] font-semibold text-[#111B21] shadow-sm" lang={langAttr(m.language)}>
          {m.text}
        </div>
        <div className="mt-1 space-y-1">
          {(m.options ?? []).map((o) => (
            <div key={o} className="rounded-xl bg-white px-3 py-2 text-center text-[14px] font-medium text-[#027EB5] shadow-sm" lang={langAttr(m.language)}>
              {o}
            </div>
          ))}
        </div>
      </motion.div>
    );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: EASE }}
      className={`my-1.5 flex ${mine ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[86%] rounded-xl px-3 py-2 text-[14px] leading-snug text-[#111B21] shadow-sm ${
          mine ? "rounded-tr-sm bg-[#D9FDD3]" : "rounded-tl-sm bg-white"
        }`}
        lang={langAttr(m.language)}
      >
        {m.kind === "voice" && <VoiceNote />}
        {m.kind === "enrolled" && (
          <p className="mb-1 flex items-center gap-1.5 text-[13px] font-semibold text-green-text">
            <CircleCheck className="size-4" aria-hidden /> Joined · Festive Scheme
          </p>
        )}
        {m.kind === "survey" ? <Survey m={m} /> : m.text && <p className="whitespace-pre-line">{m.text}</p>}
        {m.card && (
          <dl className="mt-2 space-y-1.5 rounded-lg bg-[#F0F2F5] p-2.5 text-[13px]">
            <Row k="Your October target" v={m.card.target} strong />
            <Row k="Hit it" v={m.card.hit} />
            <Row k={`Reach ${m.card.stretch}`} v={m.card.beat} />
          </dl>
        )}
        {m.note && <p className="mt-1 text-[11px] text-[#667781]">{m.note}</p>}
        <Meta m={m} mine={mine} />
      </div>
    </motion.div>
  );
}

function Row({ k, v, strong }: { k: string; v: string; strong?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-[#54656F]">{k}</dt>
      <dd className={`text-right ${strong ? "font-semibold" : "font-medium"} text-[#111B21]`}>{v}</dd>
    </div>
  );
}

function VoiceNote() {
  const bars = [6, 12, 9, 16, 11, 18, 8, 14, 10, 17, 7, 13, 9, 15, 6, 12, 10, 8];
  return (
    <div className="mb-2 flex items-center gap-2.5" aria-label="Voice note, 45 seconds">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[#00A884] text-white">
        <Play className="ml-0.5 size-4" fill="currentColor" aria-hidden />
      </span>
      <span className="flex h-6 items-center gap-[2px]">
        {bars.map((h, i) => (
          <motion.span
            key={i}
            className="w-[3px] rounded-full bg-[#8696A0]"
            initial={{ height: 3 }}
            animate={{ height: h }}
            transition={{ duration: 0.5, ease: EASE, delay: i * 0.02 }}
          />
        ))}
      </span>
      <span className="text-[12px] text-[#667781]">0:45</span>
    </div>
  );
}

function Survey({ m }: { m: Message }) {
  return (
    <div>
      <p className="text-[12px] font-semibold text-[#54656F]">Survey · {m.seconds} seconds</p>
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[13px]">
        {(m.answers ?? []).map((a) => (
          <div key={a.q} className="contents">
            <dt className="text-[#54656F]">{a.q}</dt>
            <dd className="font-medium">{a.a}</dd>
          </div>
        ))}
      </dl>
      {m.text && <p className="mt-1.5 italic">“{m.text}”</p>}
    </div>
  );
}

export function Typing() {
  return (
    <div className="my-1.5 flex" aria-label="Emami Distributor Desk is typing">
      <div className="flex gap-1 rounded-xl rounded-tl-sm bg-white px-3 py-3 shadow-sm">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="size-1.5 rounded-full bg-[#8696A0]"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </div>
  );
}
