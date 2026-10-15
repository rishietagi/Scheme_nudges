import { Placeholder } from "@/components/cards/Placeholder";
import { PageHeader } from "@/components/shell/PageHeader";

export default function DistributorViewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Distributor view"
        badge="Simulated WhatsApp · Festive Scheme loop"
        title="What the distributor sees, start to finish"
      />
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.4fr_1fr]">
        <div className="space-y-4">
          <Placeholder title="Play a scenario" phase={5} />
          <Placeholder title="Distributor" phase={5} />
        </div>
        <section className="grid min-h-[520px] place-items-center rounded-[var(--radius-card)] bg-navy-800 p-6 text-center text-white/70">
          <p className="text-[14px]">Phone preview · Phase 5</p>
        </section>
        <Placeholder title="Behind the conversation" phase={5} lines={6} />
      </div>
    </>
  );
}
