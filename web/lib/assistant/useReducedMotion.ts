"use client";

/*
 * useReducedMotion — SSR-safe prefers-reduced-motion for components that
 * don't already pull in motion/react (which has its own useReducedMotion,
 * still the right choice inside framer-motion trees like CopilotDock's
 * GenCard). This is the lighter primitive for plain CSS transitions (e.g. the
 * chat panel's slide-in) that shouldn't need the animation library just to
 * read a media query.
 *
 * Built on useSyncExternalStore (same pattern DisclaimerModal.tsx already
 * uses for its localStorage read) rather than useState+useEffect: reading
 * matchMedia().matches and calling setState synchronously inside an effect
 * is a react-hooks/set-state-in-effect lint violation (cascading renders);
 * useSyncExternalStore is the store-subscription primitive built for exactly
 * this "read a browser-only source of truth, with an SSR fallback" shape.
 *
 * readPrefersReducedMotion is exported separately so it can be unit-tested
 * without a DOM: it only needs an object shaped like `{ matchMedia }`.
 */

import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

interface MatchMediaHost {
  matchMedia?: (query: string) => MediaQueryList;
}

export function readPrefersReducedMotion(host: MatchMediaHost | undefined): boolean {
  if (!host || typeof host.matchMedia !== "function") return false;
  try {
    return host.matchMedia(QUERY).matches;
  } catch {
    return false;
  }
}

function currentHost(): MatchMediaHost | undefined {
  return typeof window === "undefined" ? undefined : window;
}

function subscribe(onStoreChange: () => void): () => void {
  const host = currentHost();
  if (!host || typeof host.matchMedia !== "function") return () => undefined;

  const mql = host.matchMedia(QUERY);
  if (typeof mql.addEventListener === "function") {
    mql.addEventListener("change", onStoreChange);
    return () => mql.removeEventListener("change", onStoreChange);
  }
  // Safari < 14 fallback — addEventListener isn't there yet.
  mql.addListener(onStoreChange);
  return () => mql.removeListener(onStoreChange);
}

function getSnapshot(): boolean {
  return readPrefersReducedMotion(currentHost());
}

function getServerSnapshot(): boolean {
  return false;
}

export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
