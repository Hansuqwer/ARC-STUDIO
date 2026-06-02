/**
 * Parity test: the TypeScript IRGraph mirror must structurally accept the
 * Python-generated IR fixtures (the source of truth lives in
 * python/src/agent_runtime_cockpit/swarmgraph_ir/models.py).
 */
import * as fs from 'fs';
import * as path from 'path';
import { IRGraph, IRNode, IR_SCHEMA_VERSION } from './swarmgraph-ir';

const FIX = path.join(__dirname, 'fixtures', 'swarmgraph-ir');

function load(name: string): IRGraph {
  return JSON.parse(fs.readFileSync(path.join(FIX, name), 'utf-8')) as IRGraph;
}

describe('SwarmGraph IR TypeScript mirror', () => {
  it('accepts the native_minimal Python fixture', () => {
    const g = load('native_minimal.ir.json');
    expect(g.ir_version).toBe(IR_SCHEMA_VERSION);
    expect(g.runtime).toBe('native');
    expect(g.provenance.adapter_id).toBeDefined();
    expect(Array.isArray(g.nodes)).toBe(true);
    expect(typeof g.graph_hash).toBe('string');
  });

  it('exposes typed MCP tool refs from the mcp_graph fixture', () => {
    const g = load('mcp_graph.ir.json');
    const mcpNode: IRNode | undefined = g.nodes.find((n) => n.kind === 'mcp_tool');
    expect(mcpNode).toBeDefined();
    expect(mcpNode!.mcp_tool).toBeDefined();
    expect(mcpNode!.mcp_tool!.server_id).toBe('fs');
    expect(mcpNode!.mcp_tool!.tool_name).toBe('write_file');
  });

  it('every node carries a risk block and side_effects array', () => {
    const g = load('native_minimal.ir.json');
    for (const node of g.nodes) {
      expect(node.risk).toBeDefined();
      expect(Array.isArray(node.side_effects)).toBe(true);
      expect(Array.isArray(node.capabilities)).toBe(true);
    }
  });
});
