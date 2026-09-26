import { existsSync, readFileSync, statSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { dirname, extname, resolve as resolvePath } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const sourceExtensions = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

function sourceFile(pathname) {
  if (existsSync(pathname) && statSync(pathname).isFile()) return pathname;
  if (extname(pathname)) return null;

  for (const extension of sourceExtensions) {
    const candidate = `${pathname}${extension}`;
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }

  for (const extension of sourceExtensions) {
    const candidate = resolvePath(pathname, `index${extension}`);
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }

  return null;
}

function sourceUrl(pathname) {
  const file = sourceFile(pathname);
  return file ? pathToFileURL(file).href : null;
}

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith("@/")) {
    const resolved = sourceUrl(resolvePath(webRoot, specifier.slice(2)));
    if (!resolved) throw new Error(`Cannot resolve frontend alias: ${specifier}`);
    return { url: resolved, format: "module", shortCircuit: true };
  }

  try {
    return await nextResolve(specifier, context);
  } catch (error) {
    if (!specifier.startsWith(".") || !context.parentURL?.startsWith("file:")) {
      throw error;
    }

    const parentDirectory = dirname(fileURLToPath(context.parentURL));
    const resolved = sourceUrl(resolvePath(parentDirectory, specifier));
    if (!resolved) throw error;
    return { url: resolved, format: "module", shortCircuit: true };
  }
}

export async function load(url, context, nextLoad) {
  if (url.endsWith(".ts") || url.endsWith(".tsx")) {
    return {
      format: "module",
      shortCircuit: true,
      source: stripTypeScriptTypes(readFileSync(fileURLToPath(url), "utf8"), {
        mode: "strip",
        sourceMap: false,
      }),
    };
  }
  return nextLoad(url, context);
}
