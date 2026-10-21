// The mascot web components (lib/motion), as JSX elements.
import "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "sarce-mark": {
        state?: string;
        size?: number | string;
        eyes?: "true" | "false";
        progress?: number | string;
        reduced?: "true" | "false";
        loop?: "true" | "false";
        speed?: number | string;
        class?: string;
        "aria-hidden"?: boolean | "true" | "false";
      };
      "sarce-skit": {
        name?: string;
        reduced?: "true" | "false";
        speed?: number | string;
        class?: string;
        "aria-hidden"?: boolean | "true" | "false";
      };
    }
  }
}
