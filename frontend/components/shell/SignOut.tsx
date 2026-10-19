"use client";

import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import { LogOut } from "lucide-react";

const signedIn = () => document.cookie.split("; ").some((c) => c === "emami_dx_signed_in=1");

/** Only on the hosted review copy (where sign-in is on). */
export function SignOut() {
  const router = useRouter();
  const show = useSyncExternalStore(
    () => () => {},
    signedIn,
    () => false,
  );
  if (!show) return null;
  return (
    <button
      type="button"
      onClick={async () => {
        await fetch("/auth/logout", { method: "POST" }).catch(() => {});
        router.replace("/login");
      }}
      className="ml-auto grid size-11 place-items-center rounded-xl text-white/60 hover:bg-white/10 hover:text-white"
      aria-label="Sign out"
      title="Sign out"
    >
      <LogOut className="size-4" aria-hidden />
    </button>
  );
}
