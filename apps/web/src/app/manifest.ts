import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Sarce",
    short_name: "Sarce",
    description: "A style-development companion for your chess games.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafbfc",
    theme_color: "#2f5f9e",
    icons: [
      { src: "/brand/sarce-app-icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/brand/sarce-app-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
