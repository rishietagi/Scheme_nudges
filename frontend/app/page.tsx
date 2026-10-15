import { Placeholder } from "@/components/cards/Placeholder";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { Stagger, StaggerItem } from "@/components/motion/Motion";
import { PageHeader } from "@/components/shell/PageHeader";

export default function CommandCentre() {
  return (
    <>
      <PageHeader eyebrow="Festive Scheme · Oct 2026 · Kolkata North · 86 distributors" title="Good morning, Rahul" />
      <LoopStepper />
      <Stagger className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {["Replied to the survey", "Joined the scheme so far", "Waiting for your approval", "Need individual attention"].map((t) => (
          <StaggerItem key={t}>
            <Placeholder title={t} phase={5} lines={2} />
          </StaggerItem>
        ))}
      </Stagger>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.25fr_1fr]">
        <Placeholder title="Needs you today" phase={5} />
        <Placeholder title="Emami AI · first week in short" phase={5} />
      </div>
      <Placeholder title="Progress by cohort" phase={5} lines={5} className="mt-4" />
    </>
  );
}
