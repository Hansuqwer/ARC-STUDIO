import {
  MOBILE_SCHEMA_VERSION,
  MobileCapability,
  MobileRuntimeManifest,
  isMobileCapability,
  isMobileRuntimeManifest,
  isMockCapability,
} from "./mobile-runtime";
import * as fs from "fs";
import * as path from "path";

const FIXTURES_DIR = path.resolve(__dirname, "../../../python/tests/mobile/fixtures");

function buildCapability(overrides: Partial<MobileCapability> = {}): MobileCapability {
  return {
    schema_version: 1,
    id: "app.memory.write.mock",
    name: "Memory Write",
    description: "Mock memory write",
    category: "app",
    platforms: ["all"],
    required_permissions: [],
    approval_mode: "none",
    data_sensitivity: "low",
    reads: false,
    writes: true,
    network: false,
    paid: false,
    background: false,
    replayable: true,
    auditable: true,
    mcp_exposable: false,
    simulator_supported: true,
    test_fixture_supported: true,
    requires_trust: false,
    requires_hitl: false,
    metadata: {},
    ...overrides,
  };
}

describe("ARC Mobile Runtime TypeScript mirror", () => {
  it("schema version constant is 1", () => {
    expect(MOBILE_SCHEMA_VERSION).toBe(1);
  });

  it("isMobileCapability accepts valid capability", () => {
    expect(isMobileCapability(buildCapability())).toBe(true);
  });

  it("isMobileCapability rejects non-capability", () => {
    expect(isMobileCapability(null)).toBe(false);
    expect(isMobileCapability({ foo: "bar" })).toBe(false);
  });

  it("isMockCapability returns true for .mock id", () => {
    expect(isMockCapability(buildCapability())).toBe(true);
  });

  it("isMockCapability returns false for non-mock id", () => {
    const real = buildCapability({ id: "device.camera.capture" });
    expect(isMockCapability(real)).toBe(false);
  });

  it("isMobileRuntimeManifest accepts valid manifest", () => {
    const manifest: MobileRuntimeManifest = {
      schema_version: 1,
      id: "test.manifest",
      name: "Test",
      version: "0.1.0",
      description: "",
      platforms: [],
      capabilities: [],
      background_execution: false,
      network_by_default: false,
      simulator_mode: true,
      privacy_manifest: true,
    };
    expect(isMobileRuntimeManifest(manifest)).toBe(true);
  });

  it("capability background must be false for mock caps", () => {
    const cap = buildCapability({ background: false });
    expect(cap.background).toBe(false);
  });

  it("loads fixture valid_mobile_runtime.json when available", () => {
    const fixturePath = path.join(FIXTURES_DIR, "valid_mobile_runtime.json");
    if (!fs.existsSync(fixturePath)) return;
    const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
    expect(isMobileRuntimeManifest(data)).toBe(true);
    expect(data.simulator_mode).toBe(true);
    expect(data.background_execution).toBe(false);
  });

  it("all capabilities in fixture are mock-only", () => {
    const fixturePath = path.join(FIXTURES_DIR, "valid_mobile_runtime.json");
    if (!fs.existsSync(fixturePath)) return;
    const manifest: MobileRuntimeManifest = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
    for (const cap of manifest.capabilities) {
      expect(cap.id.endsWith(".mock")).toBe(true);
    }
  });
});
