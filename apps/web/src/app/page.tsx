import { HomeScreen } from "@/components/home/home-screen";
import { PilotHome } from "@/components/pilot/pilot-home";
import { PilotModePage } from "@/components/pilot/pilot-status";
import { AppShell } from "@/components/shell/app-shell";

export default function Home() {
  return <PilotModePage pilot={<PilotHome />} normal={<AppShell title="home"><HomeScreen /></AppShell>} />;
}
