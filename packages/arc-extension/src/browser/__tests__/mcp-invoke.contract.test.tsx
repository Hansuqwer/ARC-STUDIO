import * as fs from 'fs';
import * as path from 'path';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { McpWorkbenchTab } from '../tabs/McpWorkbenchTab';
import type { ArcService, McpToolInvokeResult } from '../../common/arc-protocol';

const root = path.join(__dirname, '..', '..', '..');
const read = (rel: string) => fs.readFileSync(path.join(root, 'src', rel), 'utf-8');

function stub(invoke: (tool: string, args?: Record<string, unknown>) => Promise<McpToolInvokeResult>): ArcService {
    return {
        getMcpWorkbenchStatus: jest.fn().mockResolvedValue({
            workspace: '/ws', serverCreatable: true, tools: ['arc_doctor'], resources: [],
            trust: { level: 'trusted' }, diagnostic: 'ok',
        }),
        getMcpDecisions: jest.fn().mockResolvedValue({ decisions: [] }),
        invokeMcpTool: invoke,
    } as unknown as ArcService;
}

describe('IDE MCP client invoke wiring (B2P-04)', () => {
    it('protocol declares invokeMcpTool + McpToolInvokeResult', () => {
        const p = read('common/arc-protocol.ts');
        expect(p).toMatch(/invokeMcpTool\(tool: string, args\?: Record<string, unknown>\): Promise<McpToolInvokeResult>/);
        expect(p).toMatch(/export interface McpToolInvokeResult/);
    });

    it('backend invokes via `arc mcp call` with a timeout + tolerates non-zero exit', () => {
        const s = read('node/arc-backend-service.ts');
        expect(s).toMatch(/async invokeMcpTool\(/);
        expect(s).toMatch(/'mcp', 'call'/);
        expect(s).toMatch(/timeout: 30000/);
        expect(s).toMatch(/err\?\.stdout/);
    });
});

describe('IDE MCP client invoke interaction (B2P-04c)', () => {
    beforeEach(() => jest.spyOn(window, 'confirm').mockReturnValue(true));
    afterEach(() => jest.restoreAllMocks());

    it('invokes the selected tool (confirm-gated) and renders the result + risk', async () => {
        const invoke = jest.fn().mockResolvedValue({ tool: 'arc_doctor', ok: true, data: { x: 1 }, riskLevel: 'low' });
        render(<McpWorkbenchTab arcService={stub(invoke)} />);
        await screen.findByText('Invoke Tool');
        fireEvent.change(screen.getByLabelText('Tool'), { target: { value: 'arc_doctor' } });
        fireEvent.click(screen.getByRole('button', { name: /Invoke MCP tool/i }));
        await waitFor(() => expect(invoke).toHaveBeenCalledWith('arc_doctor', {}));
        await screen.findByText('OK');
        expect(screen.getByText(/risk:low/)).toBeInTheDocument();
    });

    it('cancellation discards the in-flight result (generation guard)', async () => {
        let resolveInvoke: (r: McpToolInvokeResult) => void = () => {};
        const invoke = jest.fn().mockReturnValue(new Promise<McpToolInvokeResult>(r => { resolveInvoke = r; }));
        render(<McpWorkbenchTab arcService={stub(invoke)} />);
        await screen.findByText('Invoke Tool');
        fireEvent.change(screen.getByLabelText('Tool'), { target: { value: 'arc_doctor' } });
        fireEvent.click(screen.getByRole('button', { name: /Invoke MCP tool/i }));
        fireEvent.click(await screen.findByRole('button', { name: /Cancel MCP tool invocation/i }));
        resolveInvoke({ tool: 'arc_doctor', ok: true, data: { x: 1 } });
        await waitFor(() => expect(screen.getByText(/Invocation cancelled/)).toBeInTheDocument());
        expect(screen.queryByText('OK')).not.toBeInTheDocument();
    });
});
