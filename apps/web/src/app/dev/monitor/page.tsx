import { AppShell } from "@/components/shell/app-shell";
import { MonitorView } from "@/components/dev/monitor-view";

/* Developer mode: the analysis monitor (machines, engines per game, resources, throughput, events). */
export default function MonitorPage() {
  return (
    <AppShell title="monitor">
      <MonitorView />
    </AppShell>
  );
}
