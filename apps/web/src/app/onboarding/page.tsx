import { OnboardingFlow } from "@/components/onboarding/onboarding-flow";
import { AppShell } from "@/components/shell/app-shell";

export default function OnboardingPage() {
  return (
    <AppShell title="welcome">
      <OnboardingFlow />
    </AppShell>
  );
}
