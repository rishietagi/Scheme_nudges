import { Placeholder } from "@/components/cards/Placeholder";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { PageHeader } from "@/components/shell/PageHeader";

const CARDS = ["Did they join?", "Did joining pay off?", "How fast did they react?", "What did they ask for on Day 0?"];

export default function ResultsPage() {
  return (
    <>
      <PageHeader eyebrow="Day 30 · Sat 31 Oct · Festive Scheme results" title="Results arrive on Day 30" />
      <LoopStepper />
      <div className="grid gap-4 lg:grid-cols-2">
        {CARDS.map((c) => (
          <Placeholder key={c} title={c} phase={6} lines={4} />
        ))}
        <Placeholder title="Which follow-up worked?" phase={6} lines={4} />
        <Placeholder title="What we learned" phase={6} lines={4} />
      </div>
    </>
  );
}
