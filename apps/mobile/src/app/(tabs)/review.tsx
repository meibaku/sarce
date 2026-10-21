/** Review tab: the latest game's review (older games open from Home, the library and Recap). */
import { router } from "expo-router";
import { Edge, Loading, Screen } from "@/components/ui";
import { ReviewBody } from "@/components/review";
import { getHome } from "@/lib/api";
import { useLoad } from "@/lib/use-load";

export default function ReviewTab() {
  const { data, failed, reload } = useLoad(getHome);
  if (data?.latest) return <ReviewBody gameId={data.latest.gameId} />;
  return (
    <Screen title="review">
      {failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : !data ? <Loading /> : <Edge kind="no-games" action="Connect an account" onAction={() => router.push("/onboarding")} />}
    </Screen>
  );
}
