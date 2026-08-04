"use strict";

const { randomUUID } = require("node:crypto");
const path = require("node:path");

const PROVIDER_STATE_ENV = "KIS_MCP_PROVIDER_STATE_FILE";

function normalizedPath(value) {
  const resolved = path.resolve(String(value));
  return process.platform === "win32" ? resolved.toLowerCase() : resolved;
}

function isSameStatePath(candidate, target) {
  return normalizedPath(candidate) === normalizedPath(target);
}

function installAtomicStateWriter({
  fsPromises = require("node:fs/promises"),
  target = process.env[PROVIDER_STATE_ENV],
  processId = process.pid,
  randomId = randomUUID,
} = {}) {
  if (!target) {
    return false;
  }

  const targetPath = path.resolve(String(target));
  const originalWriteFile = fsPromises.writeFile.bind(fsPromises);
  const originalRename = fsPromises.rename.bind(fsPromises);

  fsPromises.writeFile = async function writeFile(file, data, options) {
    if (!isSameStatePath(file, targetPath)) {
      return originalWriteFile(file, data, options);
    }

    const temporaryPath = path.join(
      path.dirname(targetPath),
      `.${path.basename(targetPath)}.${processId}.${randomId()}.tmp`,
    );
    await originalWriteFile(temporaryPath, data, options);
    return originalRename(temporaryPath, targetPath);
  };

  return true;
}

installAtomicStateWriter();

module.exports = {
  installAtomicStateWriter,
  isSameStatePath,
};
