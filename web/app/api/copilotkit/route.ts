import {
  CopilotRuntime,
  copilotKitEndpoint,
  copilotRuntimeNextJSAppRouterEndpoint,
  EmptyAdapter,
  OpenAIAdapter,
} from "@copilotkit/runtime";
import OpenAI from "openai";

export const runtime = "nodejs";
// Reaches the configured model endpoint + backend at request time; never prerender/evaluate at
// build (where the key/backend are absent).
export const dynamic = "force-dynamic";

const DEFAULT_API_BASE = "http://localhost:8000";
const ROUTE_PATH = "/api/copilotkit";

function backendOriginFrom(value: string | undefined) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.pathname === "/" || url.pathname === "") return url.origin;
    const pathname = url.pathname.replace(/\/$/, "");
    if (pathname === "/api/v1") return url.origin;
    url.pathname = pathname;
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return value.replace(/\/$/, "");
  }
}

const apiBase =
  backendOriginFrom(process.env.API_BASE) ??
  backendOriginFrom(process.env.NEXT_PUBLIC_API_BASE) ??
  DEFAULT_API_BASE;

const copilotRuntime = new CopilotRuntime({
  remoteEndpoints: [copilotKitEndpoint({ url: `${apiBase}/copilotkit` })],
});

type RouteHandler = ReturnType<
  typeof copilotRuntimeNextJSAppRouterEndpoint
>["handleRequest"];

let cachedHandler: RouteHandler | undefined;

function getHandler(): RouteHandler {
  if (!cachedHandler) {
    // OpenAI's SDK is used only as the server-side transport client for the
    // standard OpenAI-compatible protocol. The endpoint and credentials stay
    // deployment-configurable and never enter the browser bundle.
    const enabled = parseBoolean(process.env.MODEL_ENABLED, true);
    const provider = (process.env.INTELLIGENCE_PROVIDER ?? "generic").toLowerCase();
    const model = process.env.MODEL_NAME;
    const key = process.env.MODEL_API_KEY;
    const baseURL = process.env.MODEL_BASE_URL;
    const openaiEnabled = parseBoolean(process.env.OPENAI_ENABLED, false);
    const openaiKey = process.env.OPENAI_API_KEY;
    const openaiModel = process.env.OPENAI_MODEL;
    const useOpenAI = provider === "openai" && openaiEnabled && hasRuntimeValue(openaiKey) && hasRuntimeValue(openaiModel);
    const useGeneric = provider === "generic" && hasRuntimeValue(key) && hasRuntimeValue(baseURL) && hasRuntimeValue(model);

    const serviceAdapter = enabled && (useOpenAI || useGeneric)
      ? new OpenAIAdapter({
          openai: new OpenAI({
            apiKey: useOpenAI ? openaiKey : key,
            baseURL: useOpenAI ? undefined : baseURL,
            timeout: Number(process.env.MODEL_TIMEOUT_SECONDS ?? "45") * 1000,
            maxRetries: Number(process.env.MODEL_MAX_RETRIES ?? "2"),
          }),
          model: useOpenAI ? openaiModel : model,
        })
      : new EmptyAdapter();

    cachedHandler = copilotRuntimeNextJSAppRouterEndpoint({
      runtime: copilotRuntime,
      serviceAdapter,
      endpoint: ROUTE_PATH,
    }).handleRequest;
  }
  return cachedHandler;
}

function parseBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  return ["1", "true", "yes", "on", "enabled"].includes(value.toLowerCase());
}

function hasRuntimeValue(value: string | undefined): value is string {
  if (!value?.trim()) return false;
  const normalized = value.trim().toUpperCase();
  return !normalized.startsWith("REPLACE_WITH_") && !normalized.includes("CHANGE_ME");
}

export const GET: RouteHandler = (req) => getHandler()(req);
export const POST: RouteHandler = (req) => getHandler()(req);
export const OPTIONS: RouteHandler = (req) => getHandler()(req);
