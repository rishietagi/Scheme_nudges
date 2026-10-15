"use client";

import { motion } from "motion/react";
import { EASE } from "@/components/motion/Motion";

// Re-mounts on every navigation: a short, calm fade-up between pages.
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE }}>
      {children}
    </motion.div>
  );
}
