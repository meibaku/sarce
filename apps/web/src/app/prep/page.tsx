import { PrepView } from "@/components/prep/prep-view";
import { AppShell } from "@/components/shell/app-shell";

export default function PrepPage() {
  return (
    <AppShell title="play">
      <PrepView />
    </AppShell>
  );
}
