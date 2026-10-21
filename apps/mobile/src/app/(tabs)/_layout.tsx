/** The phone tab bar (handoff): Home, Review, You, Train, Play. Settings sits in the header. */
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { T } from "@/components/ui";
import { color, font } from "@/lib/theme";

const icon = (glyph: string) =>
  function TabIcon({ color: tint }: { color: ColorValue }) {
    return <T size={17} style={{ color: tint, lineHeight: 20 }}>{glyph}</T>;
  };

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: color.accentText,
        tabBarInactiveTintColor: color.muted,
        tabBarStyle: { backgroundColor: color.surface, borderTopColor: color.line },
        tabBarLabelStyle: { fontFamily: font.medium, fontSize: 11 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: icon("⌂") }} />
      <Tabs.Screen name="review" options={{ title: "Review", tabBarIcon: icon("⌕") }} />
      <Tabs.Screen name="you" options={{ title: "You", tabBarIcon: icon("◯") }} />
      <Tabs.Screen name="train" options={{ title: "Train", tabBarIcon: icon("↻") }} />
      <Tabs.Screen name="play" options={{ title: "Play", tabBarIcon: icon("▷") }} />
    </Tabs>
  );
}
