import assert from "node:assert/strict";
import test from "node:test";
import { readPrefersReducedMotion } from "@/lib/assistant/useReducedMotion";

test("readPrefersReducedMotion: false when host is undefined (SSR)", () => {
  assert.equal(readPrefersReducedMotion(undefined), false);
});

test("readPrefersReducedMotion: false when host has no matchMedia", () => {
  assert.equal(readPrefersReducedMotion({}), false);
});

test("readPrefersReducedMotion: reflects matchMedia().matches", () => {
  const host = { matchMedia: (_query: string) => ({ matches: true }) as MediaQueryList };
  assert.equal(readPrefersReducedMotion(host), true);
});

test("readPrefersReducedMotion: false when matchMedia throws", () => {
  const host = {
    matchMedia: (_query: string): MediaQueryList => {
      throw new Error("not supported");
    },
  };
  assert.equal(readPrefersReducedMotion(host), false);
});

test("readPrefersReducedMotion: passes the reduce-motion query string through", () => {
  let seen = "";
  const host = {
    matchMedia: (query: string) => {
      seen = query;
      return { matches: false } as MediaQueryList;
    },
  };
  readPrefersReducedMotion(host);
  assert.equal(seen, "(prefers-reduced-motion: reduce)");
});
