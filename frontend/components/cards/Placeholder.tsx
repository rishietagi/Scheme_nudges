import { Card } from "./Card";

/** Phase-0 stand-in for a card that a later phase fills in. */
export function Placeholder({ title, phase, className = "", lines = 3 }: { title: string; phase: number; className?: string; lines?: number }) {
  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="min-w-0 font-display text-[19px] font-semibold text-ink">{title}</h2>
        <span className="shrink-0 whitespace-nowrap rounded-full bg-[#EEF1F5] px-2.5 py-0.5 text-[12px] font-medium text-muted">Phase {phase}</span>
      </div>
      <div className="mt-5 space-y-3" aria-hidden>
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} className="h-3 animate-pulse rounded-full bg-track" style={{ width: `${88 - i * 17}%` }} />
        ))}
      </div>
    </Card>
  );
}
