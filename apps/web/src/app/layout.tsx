import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { PilotStatusProvider } from "@/components/pilot/pilot-status";
import { THEME_SCRIPT } from "@/lib/theme";
import "./globals.css";

const plexSans = localFont({
  src: "../../public/fonts/IBMPlexSans-400.woff2",
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = localFont({
  src: "../../public/fonts/IBMPlexMono-400.woff2",
  variable: "--font-plex-mono",
  display: "swap",
});

const plexSerif = localFont({
  src: "../../public/fonts/IBMPlexSerif-Regular.ttf",
  variable: "--font-plex-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sarce",
  description:
    "A style-development companion for your chess games: did this game feel like you, not did you play like the engine?",
};

export const viewport: Viewport = {
  themeColor: "#fafbfc",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // data-theme is set by THEME_SCRIPT before hydration, so React must not warn about it.
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className={`${plexSans.variable} ${plexMono.variable} ${plexSerif.variable} min-h-screen`}>
        <PilotStatusProvider>{children}</PilotStatusProvider>
      </body>
    </html>
  );
}
