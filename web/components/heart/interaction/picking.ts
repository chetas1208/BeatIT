export const HEART_COMPONENT_ID_KEY = "heartComponentId";

export interface SemanticUserData {
  [HEART_COMPONENT_ID_KEY]?: string;
  [key: string]: unknown;
}

export interface SemanticPickObject {
  userData?: unknown;
  parent?: SemanticPickObject | null;
}

export interface SemanticPickEvent {
  stopPropagation?: () => void;
  object?: SemanticPickObject | null;
}

export function createSemanticUserData(
  componentId: string,
  userData: SemanticUserData = {},
): SemanticUserData {
  if (!componentId) throw new Error("A semantic component ID is required.");
  return { ...userData, [HEART_COMPONENT_ID_KEY]: componentId };
}

export function getSemanticComponentId(
  object: SemanticPickObject | null | undefined,
): string | null {
  let current = object;
  const visited = new Set<SemanticPickObject>();

  while (current && !visited.has(current)) {
    visited.add(current);
    const userData = current.userData;
    if (userData && typeof userData === "object") {
      const componentId = (userData as Record<string, unknown>)[HEART_COMPONENT_ID_KEY];
      if (typeof componentId === "string" && componentId.length > 0) return componentId;
    }
    current = current.parent;
  }

  return null;
}

export function getSemanticComponentIdFromEvent(
  event: SemanticPickEvent | null | undefined,
): string | null {
  return getSemanticComponentId(event?.object);
}
