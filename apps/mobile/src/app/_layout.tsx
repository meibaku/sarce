/** Root: loads IBM Plex, then a header-less stack (screens draw their own header, as in the handoff). */
import { IBMPlexMono_400Regular, IBMPlexMono_500Medium } from "@expo-google-fonts/ibm-plex-mono";
import { IBMPlexSans_400Regular, IBMPlexSans_500Medium, IBMPlexSans_600SemiBold, useFonts } from "@expo-google-fonts/ibm-plex-sans";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { color } from "@/lib/theme";

export default function RootLayout() {
  const [loaded] = useFonts({ IBMPlexSans_400Regular, IBMPlexSans_500Medium, IBMPlexSans_600SemiBold, IBMPlexMono_400Regular, IBMPlexMono_500Medium });
  if (!loaded) return null;
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: color.page } }} />
    </>
  );
}
