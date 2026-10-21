import { useLocalSearchParams } from "expo-router";
import { ReviewBody } from "@/components/review";

export default function GameReview() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ReviewBody gameId={id} back />;
}
