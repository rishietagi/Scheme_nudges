import { PageHeader } from "@/components/shell/PageHeader";
import { Controls } from "@/components/sim/Controls";
import { LiveFeed } from "@/components/sim/LiveFeed";
import { LoopPanel } from "@/components/sim/LoopPanel";

export default function SimulationPage() {
  return (
    <>
      <PageHeader eyebrow="Demo · plays one full scheme cycle for Kolkata North" title="Simulation" badge="Simulated WhatsApp · DMS" />
      <div className="grid items-start gap-5 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_340px]">
        <Controls />
        <LoopPanel />
        <div className="lg:col-span-2 xl:col-span-1">
          <LiveFeed />
        </div>
      </div>
    </>
  );
}
