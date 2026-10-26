import Link from "next/link";
import { Card, SectionLabel } from "@/components/ui/card";

/** A separate research entry inside Train; it never replaces or grades the ordinary drill queue. */
export function LearningEvidenceCard() {
  return (
    <Card className="gap-3 md:flex-row md:items-center md:justify-between">
      <div className="flex max-w-2xl flex-col gap-1">
        <SectionLabel>Learning Evidence · invited study</SectionLabel>
        <h2 className="text-[17px] font-medium">Notice what is safe before choosing a move</h2>
        <p className="text-[13px] leading-[1.5] text-ink-2">
          A separate, consent-based study of piece-safety recognition. Your style profile and Brilliant goal stay unchanged.
        </p>
      </div>
      <Link
        href="/train/learning"
        className="inline-flex h-11 shrink-0 items-center justify-center rounded-[6px] bg-accent px-[18px] text-[13px] font-medium text-white hover:bg-accent-hover"
      >
        Open Learning Evidence
      </Link>
    </Card>
  );
}
