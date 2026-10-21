/** The phone tab bar (handoff): Home, Review, You, Train, Play. Settings sits in the header. */
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { Icon, type IconName } from "@/components/icons";
import { color, font } from "@/lib/theme";

const icon = (name: IconName) =>
  function TabIcon({ color: tint }: { color: ColorValue }) {
    return <Icon name={name} size={22} color={String(tint)} />;
  };

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: color.accentText,
        tabBarInactiveTintColor: color.muted,
        // Handoff tab bar: 22px line icons over 11px labels; tall enough that the labels are never clipped.
        tabBarStyle: { backgroundColor: color.surface, borderTopColor: color.line, height: 68, paddingTop: 6, paddingBottom: 10 },
        tabBarLabelStyle: { fontFamily: font.medium, fontSize: 11 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: icon("home") }} />
      <Tabs.Screen name="review" options={{ title: "Review", tabBarIcon: icon("review") }} />
      <Tabs.Screen name="you" options={{ title: "You", tabBarIcon: icon("you") }} />
      <Tabs.Screen name="train" options={{ title: "Train", tabBarIcon: icon("train") }} />
      <Tabs.Screen name="play" options={{ title: "Play", tabBarIcon: icon("play") }} />
    </Tabs>
  );
}
