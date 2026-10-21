import { HomeScreen } from "@/components/home/home-screen";
import { AppShell } from "@/components/shell/app-shell";

export default function Home() {
  return (
    <AppShell title="home">
      <HomeScreen />
    </AppShell>
  );
}
