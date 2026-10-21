/**
 * Theme (Settings → Theme). The choice is kept on this device so the inline script in app/layout.tsx
 * can set `data-theme` before the first paint, with no flash; the profile stores it too.
 */
export type ThemeChoice = "light" | "dark" | "system";

export const THEME_KEY = "sarce.theme";

/** Runs in <head> before React: resolves the stored choice (and the OS setting for "system"). */
export const THEME_SCRIPT = `(function(){try{var k=${JSON.stringify(THEME_KEY)};var m=window.matchMedia("(prefers-color-scheme: dark)");var a=function(){var t=localStorage.getItem(k)||"light";document.documentElement.dataset.theme=t==="dark"||(t==="system"&&m.matches)?"dark":"light"};a();m.addEventListener("change",a);window.addEventListener("storage",a)}catch(e){}})();`;

export function applyTheme(choice: ThemeChoice) {
  try {
    window.localStorage.setItem(THEME_KEY, choice);
  } catch {
    // Storage blocked (private window): still apply it for this page.
  }
  const dark = choice === "dark" || (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}
