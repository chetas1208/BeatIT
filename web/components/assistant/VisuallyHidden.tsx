/*
 * VisuallyHidden — content that screen readers announce but sighted users
 * never see (e.g. a label for an icon-only trigger, or a chat-panel heading
 * that gives the region a name without duplicating on-screen text). No repo
 * equivalent existed under web/components or web/lib as of Wave 4; this is
 * the standard clip-not-display pattern so the node stays in the accessibility
 * tree and keyboard/AT focus (unlike `display:none` / `hidden`).
 *
 * Built with createElement rather than JSX: a generic `ElementType` used
 * directly as a JSX tag narrows its props to `never` (TS2745) because JSX
 * can't resolve which intrinsic/component prop shape applies. createElement's
 * ElementType overload doesn't have that restriction.
 */

import { createElement, type CSSProperties, type ElementType, type ReactNode } from "react";

const HIDDEN_STYLE: CSSProperties = {
  position: "absolute",
  width: "1px",
  height: "1px",
  padding: 0,
  margin: "-1px",
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0,
};

export function VisuallyHidden({
  as = "span",
  children,
}: {
  as?: ElementType;
  children: ReactNode;
}) {
  return createElement(as, { style: HIDDEN_STYLE }, children);
}
