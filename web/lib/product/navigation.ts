import { BEATIT_MODES, isBeatITMode, type BeatITMode } from "./contracts";

export function modeFromPathname(pathname: string): BeatITMode {
  const segment = pathname.replace(/^\//, "").split("/")[0] ?? "";
  return isBeatITMode(segment) ? segment : "twin";
}

export function pathForMode(mode: BeatITMode): string {
  return `/${mode}`;
}

export function allProductPaths(): readonly string[] {
  return BEATIT_MODES.map(pathForMode);
}

/** Only mode paths are written to browser history; no patient or payload data is encoded. */
export function navigateToMode(mode: BeatITMode): void {
  if (typeof window === "undefined") return;
  window.history.pushState({ beatItMode: mode }, "", pathForMode(mode));
  window.dispatchEvent(new PopStateEvent("popstate"));
}
