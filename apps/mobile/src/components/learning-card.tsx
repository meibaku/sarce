import { router } from "expo-router";
import { Card, Label, Primary, T } from "@/components/ui";

/** Separate research entry inside Train; it does not replace the normal drill queue. */
export function LearningEvidenceCard() {
  return (
    <Card>
      <Label>Learning Evidence · invited study</Label>
      <T weight="medium" size={17}>Notice what is safe before choosing a move</T>
      <T size={13} tone="ink2">
        A consent-based piece-safety study. Your style profile and Brilliant goal stay unchanged.
      </T>
      <Primary label="Open Learning Evidence" onPress={() => router.push("/learning")} />
    </Card>
  );
}
