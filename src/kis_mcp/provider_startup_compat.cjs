"use strict";

const INSTALL_MARKER = Symbol.for("kis-mcp.provider-startup-compat.installed");

function requestUrl(input) {
  if (typeof input === "string") {
    return input;
  }
  if (input && typeof input.url === "string") {
    return input.url;
  }
  return String(input);
}

function createContainedFetch({ originalFetch, flagUrl, ResponseClass }) {
  if (typeof originalFetch !== "function") {
    throw new TypeError("originalFetch must be a function");
  }
  if (typeof ResponseClass !== "function") {
    throw new TypeError("ResponseClass must be a constructor");
  }

  return async function containedFetch(input, init) {
    if (flagUrl && requestUrl(input) === flagUrl) {
      return new ResponseClass(JSON.stringify({ flags: {} }), {
        status: 200,
        headers: {
          "cache-control": "no-store",
          "content-type": "application/json",
        },
      });
    }
    if (arguments.length === 1) {
      return originalFetch(input);
    }
    return originalFetch(input, init);
  };
}

function callbackFrom(encoding, callback) {
  if (typeof encoding === "function") {
    return encoding;
  }
  return typeof callback === "function" ? callback : null;
}

function parseJsonRpcChunk(chunk, encoding) {
  if (typeof chunk !== "string" && !Buffer.isBuffer(chunk)) {
    return null;
  }
  const text = Buffer.isBuffer(chunk)
    ? chunk.toString(typeof encoding === "string" ? encoding : "utf8")
    : chunk;
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
    return null;
  }
  try {
    return { message: JSON.parse(trimmed), text };
  } catch {
    return null;
  }
}

function sanitizeToolCatalogue(message) {
  const tools = message?.result?.tools;
  if (!Array.isArray(tools)) {
    return message;
  }

  const result = { ...message.result };
  delete result._meta;
  delete result.meta;
  result.tools = tools.map((tool) => {
    if (!tool || typeof tool !== "object" || Array.isArray(tool)) {
      return tool;
    }
    const sanitized = { ...tool };
    delete sanitized._meta;
    delete sanitized.meta;
    return sanitized;
  });
  return { ...message, result };
}

function renderJsonRpcChunk(originalText, message) {
  const newline = originalText.endsWith("\r\n")
    ? "\r\n"
    : originalText.endsWith("\n")
      ? "\n"
      : "";
  return JSON.stringify(message) + newline;
}

function createFilteredStdoutWrite({ originalWrite }) {
  if (typeof originalWrite !== "function") {
    throw new TypeError("originalWrite must be a function");
  }

  return function filteredStdoutWrite(chunk, encoding, callback) {
    const parsed = parseJsonRpcChunk(chunk, encoding);
    if (parsed?.message?.method === "notifications/message") {
      const done = callbackFrom(encoding, callback);
      if (done) {
        done();
      }
      return true;
    }

    if (parsed && Array.isArray(parsed.message?.result?.tools)) {
      const rendered = renderJsonRpcChunk(
        parsed.text,
        sanitizeToolCatalogue(parsed.message),
      );
      return originalWrite(rendered, encoding, callback);
    }

    return originalWrite(chunk, encoding, callback);
  };
}

function installStartupCompatibility({
  globalObject = globalThis,
  stdout = process.stdout,
  flagUrl = process.env.KIS_MCP_PROVIDER_FLAG_URL,
} = {}) {
  if (globalObject[INSTALL_MARKER]) {
    return;
  }

  if (typeof globalObject.fetch === "function" && flagUrl) {
    globalObject.fetch = createContainedFetch({
      originalFetch: globalObject.fetch.bind(globalObject),
      flagUrl,
      ResponseClass: globalObject.Response,
    });
  }

  const originalWrite = stdout.write.bind(stdout);
  stdout.write = createFilteredStdoutWrite({ originalWrite });
  globalObject[INSTALL_MARKER] = true;
}

module.exports = {
  createContainedFetch,
  createFilteredStdoutWrite,
  installStartupCompatibility,
  sanitizeToolCatalogue,
};

if (process.env.KIS_MCP_PROVIDER_STARTUP_COMPAT === "1") {
  installStartupCompatibility();
}
