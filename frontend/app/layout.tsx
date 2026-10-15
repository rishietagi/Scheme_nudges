import type { Metadata } from "next";
import { Bricolage_Grotesque, Instrument_Sans, Noto_Sans_Bengali, Noto_Sans_Devanagari } from "next/font/google";
import { Suspense } from "react";
import { AppShell } from "@/components/shell/AppShell";
import "./globals.css";

const instrument = Instrument_Sans({ variable: "--font-instrument", subsets: ["latin"], display: "swap" });
const bricolage = Bricolage_Grotesque({ variable: "--font-bricolage", subsets: ["latin"], display: "swap" });
const bengali = Noto_Sans_Bengali({ variable: "--font-bengali", subsets: ["bengali"], display: "swap" });
const devanagari = Noto_Sans_Devanagari({ variable: "--font-devanagari", subsets: ["devanagari"], display: "swap" });

export const metadata: Metadata = {
  title: "Emami — Distributor Experience Platform",
  description: "Concept prototype on synthetic data: nudge, survey, follow-up and 30-day check for every scheme.",
  icons: { icon: "/brand/emami-logo.png" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${instrument.variable} ${bricolage.variable} ${bengali.variable} ${devanagari.variable} h-full`}
    >
      <body className="min-h-full">
        <Suspense>
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
