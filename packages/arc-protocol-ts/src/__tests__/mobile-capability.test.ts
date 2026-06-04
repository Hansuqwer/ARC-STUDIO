import * as fs from 'fs';
import * as path from 'path';
import { isMobileRuntimeManifest, type MobileCapabilityManifest } from '../mobile-capability';

const FIXTURE = path.resolve(__dirname, '../../../../runtimes/mobile/fixtures/capabilities.safe-demo.json');

describe('mobile capability protocol mirror', () => {
  it('loads safe demo manifest', () => {
    const manifest = JSON.parse(fs.readFileSync(FIXTURE, 'utf8')) as MobileCapabilityManifest;
    expect(isMobileRuntimeManifest(manifest)).toBe(true);
    expect(manifest.simulator_mode).toBe(true);
    expect(manifest.background_execution).toBe(false);
    expect(manifest.network_by_default).toBe(false);
  });

  it('keeps MVP capabilities mock-only and MCP-closed', () => {
    const manifest = JSON.parse(fs.readFileSync(FIXTURE, 'utf8')) as MobileCapabilityManifest;
    for (const cap of manifest.capabilities) {
      expect(cap.id.endsWith('.mock')).toBe(true);
      expect(cap.mcp_exposable).toBe(false);
      expect(cap.simulator_supported).toBe(true);
    }
  });
});
