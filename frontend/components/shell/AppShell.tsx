"use client";

import { AnimatePresence, motion, MotionConfig } from "motion/react";
import Image from "next/image";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { SimProvider } from "@/lib/sim";
import { EASE } from "@/components/motion/Motion";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <MotionConfig reducedMotion="user">
      <SimProvider>
        <div className="min-h-screen lg:pl-[232px]">
          {/* Desktop sidebar */}
          <aside className="fixed inset-y-0 left-0 hidden w-[232px] overflow-y-auto bg-navy-900 lg:block">
            <Sidebar />
          </aside>

          {/* Mobile / tablet top bar + drawer */}
          <header className="sticky top-0 z-30 flex items-center justify-between bg-navy-900 px-4 py-2.5 lg:hidden">
            <Image src="/brand/emami-logo-reverse.png" alt="Emami" width={44} height={40} className="h-auto w-[44px]" />
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="grid size-11 place-items-center rounded-xl text-white hover:bg-white/10"
              aria-label="Open menu"
            >
              <Menu className="size-5" />
            </button>
          </header>
          <AnimatePresence>
            {open && (
              <>
                <motion.div
                  className="fixed inset-0 z-40 bg-navy-900/40 backdrop-blur-[2px] lg:hidden"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setOpen(false)}
                />
                <motion.aside
                  className="fixed inset-y-0 left-0 z-50 w-[260px] overflow-y-auto lg:hidden"
                  initial={{ x: -280 }}
                  animate={{ x: 0 }}
                  exit={{ x: -280 }}
                  transition={{ duration: 0.35, ease: EASE }}
                >
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="absolute right-3 top-3 z-10 grid size-11 place-items-center rounded-xl text-white hover:bg-white/10"
                    aria-label="Close menu"
                  >
                    <X className="size-5" />
                  </button>
                  <Sidebar onNavigate={() => setOpen(false)} layoutId="nav-active-mobile" />
                </motion.aside>
              </>
            )}
          </AnimatePresence>

          <main className="mx-auto max-w-[1200px] px-4 pb-16 pt-6 sm:px-6 lg:px-9 lg:pt-8">{children}</main>
        </div>
      </SimProvider>
    </MotionConfig>
  );
}
