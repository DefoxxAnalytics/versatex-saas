/**
 * Drift-guard for v2.12 streamdown version pin (security audit posture).
 *
 * The v2.12 audit pinned `streamdown` to an exact version (no `^` / `~`) after
 * verifying its sanitization behavior for the AI streaming chat surface. If
 * anyone bumps the version (or loosens the range) without re-auditing, this
 * test fails first — forcing the developer to consciously reset the audit
 * posture before the change ships.
 *
 * To intentionally update streamdown:
 *   1. Re-audit the new version's sanitization (XSS via markdown HTML
 *      passthrough, prototype pollution in the parser, etc.).
 *   2. Update the EXPECTED_STREAMDOWN_VERSION constant below to the new pin.
 *   3. Document the audit in the PR description.
 *
 * See docs/codebase-review-2026-05-06-second-pass.md for the v2.12 second-pass
 * review requesting this drift-guard.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { describe, it, expect } from "vitest";

const EXPECTED_STREAMDOWN_VERSION = "1.4.0";

// frontend/src/lib/__tests__/ -> frontend/package.json
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PACKAGE_JSON_PATH = path.resolve(__dirname, "../../../package.json");

interface PackageJson {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}

function readPackageJson(): PackageJson {
  const raw = readFileSync(PACKAGE_JSON_PATH, "utf8");
  return JSON.parse(raw) as PackageJson;
}

describe("streamdown version pin drift-guard", () => {
  it("pins streamdown to exact version (no caret/tilde range)", () => {
    // #given the frontend package.json
    const pkg = readPackageJson();

    // #when streamdown's pinned version is read
    const streamdownVersion = pkg.dependencies?.streamdown;

    // #then it matches the audited exact version with no semver-range prefix
    expect(streamdownVersion).toBe(EXPECTED_STREAMDOWN_VERSION);
  });

  it("rejects caret/tilde semver ranges on the streamdown pin", () => {
    // #given the frontend package.json
    const pkg = readPackageJson();

    // #when streamdown's pinned version is inspected for range prefixes
    const streamdownVersion = pkg.dependencies?.streamdown ?? "";

    // #then no range character is present (audit posture demands an exact pin)
    expect(streamdownVersion.startsWith("^")).toBe(false);
    expect(streamdownVersion.startsWith("~")).toBe(false);
    expect(streamdownVersion.includes(">=")).toBe(false);
    expect(streamdownVersion.includes("*")).toBe(false);
  });

  it("ensures streamdown is declared as a runtime dependency, not devDependency", () => {
    // #given the frontend package.json
    const pkg = readPackageJson();

    // #when the dep manifests are inspected
    // #then streamdown lives under dependencies (it ships to production)
    expect(pkg.dependencies?.streamdown).toBeDefined();
    expect(pkg.devDependencies?.streamdown).toBeUndefined();
  });
});
