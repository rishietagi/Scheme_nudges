"use client";

import Image from "next/image";
import { motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Eye, EyeOff, Lock } from "lucide-react";
import { EASE } from "@/components/motion/Motion";

/** In-app sign-in for the hosted review copy (works in locked-down corporate browsers, unlike the browser's own
 *  login prompt). Posts to /auth/login, which sets a session cookie, then goes back to the page that was asked for. */
export function LoginForm() {
  const params = useSearchParams();
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "That didn't work. Try again.");
        return;
      }
      const next = params.get("next");
      // Full navigation so every page reloads with the new session.
      window.location.assign(next && next.startsWith("/") && !next.startsWith("//") ? next : "/cohorts");
    } catch {
      setError("Can't reach the server. If it's been idle it may be waking up — try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-bg lg:grid-cols-[1fr_1.1fr]">
      <div className="hidden flex-col justify-between bg-navy-900 p-12 text-white lg:flex">
        <div>
          <Image src="/brand/emami-logo-reverse.png" alt="Emami" width={120} height={110} className="h-auto w-[120px]" priority />
          <p className="mt-4 text-[17px] font-semibold">Distributor Experience Platform</p>
        </div>
        <div className="max-w-md">
          <h2 className="font-display text-[34px] font-semibold leading-tight">Every scheme: a nudge, a survey, the right next action — and a 30-day check.</h2>
          <p className="mt-4 text-[16px] leading-relaxed text-white/75">
            Cohorts from business potential and performance, a survey for each cohort, next best actions you approve, and
            results that feed the next quarter.
          </p>
        </div>
        <p className="text-[13px] text-white/50">Concept prototype · synthetic data · built by KPMG for Emami</p>
      </div>

      <div className="flex items-center justify-center px-4 py-12">
        <motion.form
          onSubmit={submit}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: EASE }}
          className="w-full max-w-sm rounded-[var(--radius-card)] border border-card-border bg-white p-8 shadow-[var(--shadow-card)]"
          aria-labelledby="signin-title"
        >
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <span className="grid size-12 place-items-center rounded-xl bg-navy-900">
              <Image src="/brand/emami-logo-reverse.png" alt="Emami" width={36} height={33} className="h-auto w-9" />
            </span>
            <span className="text-[15px] font-semibold text-ink">Distributor Experience Platform</span>
          </div>
          <span className="grid size-11 place-items-center rounded-xl bg-blue-soft text-emami-blue">
            <Lock className="size-5" aria-hidden />
          </span>
          <h1 id="signin-title" className="mt-4 font-display text-[26px] font-semibold text-ink">
            Sign in
          </h1>
          <p className="mt-1 text-[14px] text-muted">Use the username and password you were sent with the link.</p>

          <label className="mt-6 block">
            <span className="text-[14px] font-medium text-ink">Username</span>
            <input
              value={user}
              onChange={(e) => setUser(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              autoFocus
              className="mt-1 h-12 w-full rounded-xl border border-card-border px-3.5 text-[15px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
            />
          </label>
          <label className="mt-4 block">
            <span className="text-[14px] font-medium text-ink">Password</span>
            <span className="relative mt-1 block">
              <input
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="h-12 w-full rounded-xl border border-card-border px-3.5 pr-12 text-[15px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                aria-label={show ? "Hide password" : "Show password"}
                className="absolute right-0.5 top-0.5 grid size-11 place-items-center rounded-lg text-muted hover:text-ink"
              >
                {show ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
              </button>
            </span>
          </label>

          {error && (
            <p className="mt-4 rounded-xl bg-red-soft px-3 py-2 text-[14px] text-red" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-navy-800 text-[15px] font-semibold text-white hover:bg-navy-900 disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
            {!busy && <ArrowRight className="size-4" aria-hidden />}
          </button>
          <p className="mt-4 text-center text-[12px] text-muted">Concept prototype · synthetic data</p>
        </motion.form>
      </div>
    </div>
  );
}
