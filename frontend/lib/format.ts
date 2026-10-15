// Sim clock: Day 0 = Thu 1 Oct 2026, 00:00 (local, no timezone games — we build the date by parts).
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function simDate(day: number): Date {
  return new Date(2026, 9, 1 + Math.floor(day));
}

/** "Day 9 · Sat 10 Oct" */
export function dayLabel(day: number): string {
  const d = simDate(day);
  return `Day ${Math.floor(day)} · ${WEEKDAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** "13:05" */
export function timeLabel(day: number): string {
  const minutes = Math.round((day - Math.floor(day)) * 1440);
  const hh = Math.floor(minutes / 60) % 24;
  const mm = minutes % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}

/** Money is stored in ₹ lakh. 1840 → "₹18.4 Cr", 38.2 → "₹38.2 L". */
export function formatINR(lakh: number): string {
  if (Math.abs(lakh) >= 100) return `₹${trim(lakh / 100)} Cr`;
  return `₹${trim(lakh)} L`;
}

function trim(x: number): string {
  return x.toFixed(1).replace(/\.0$/, "");
}

export function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}
