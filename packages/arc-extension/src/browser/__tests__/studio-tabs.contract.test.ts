/**
 * Studio Tabs Contract Tests
 *
 * Static source-pattern tests for ChatTab, RunsTab, WorkflowsTab, ConfigTab.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('Studio Tabs Contracts', () => {
    const tabsDir = path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs');

    describe('tabs/index.ts exports', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'index.ts'), 'utf-8');
        });

        it('should export ChatTab', () => {
            expect(source).toMatch(/export.*ChatTab/);
        });

        it('should export ChatTabProps', () => {
            expect(source).toMatch(/export.*ChatTabProps/);
        });

        it('should export RunsTab', () => {
            expect(source).toMatch(/export.*RunsTab/);
        });

        it('should export RunsTabProps', () => {
            expect(source).toMatch(/export.*RunsTabProps/);
        });

        it('should export WorkflowsTab', () => {
            expect(source).toMatch(/export.*WorkflowsTab/);
        });

        it('should export WorkflowsTabProps', () => {
            expect(source).toMatch(/export.*WorkflowsTabProps/);
        });

        it('should export ConfigTab', () => {
            expect(source).toMatch(/export.*ConfigTab/);
        });

        it('should export ConfigTabProps', () => {
            expect(source).toMatch(/export.*ConfigTabProps/);
        });
    });

    describe('ChatTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'ChatTab.tsx'), 'utf-8');
        });

        it('should export ChatTabProps interface', () => {
            expect(source).toMatch(/export interface ChatTabProps/);
        });

        it('should have chat input field', () => {
            expect(source).toMatch(/arc-studio-chat__input/);
            expect(source).toMatch(/arc-studio-chat__input-field/);
        });

        it('should have mode indicator', () => {
            expect(source).toMatch(/arc-studio-chat__mode/);
            expect(source).toMatch(/Mode:/);
        });

        it('should have send button', () => {
            expect(source).toMatch(/arc-studio-chat__send/);
            expect(source).toMatch(/Send/);
        });

        it('should cycle through plan/build/auto modes', () => {
            expect(source).toMatch(/plan/);
            expect(source).toMatch(/build/);
            expect(source).toMatch(/auto/);
            expect(source).toMatch(/cycleMode/);
        });

        it('should have placeholder text', () => {
            expect(source).toMatch(/arc-studio-chat__placeholder/);
        });

        it('should load runtime capabilities for disabled selector states', () => {
            expect(source).toMatch(/listRuntimeCapabilities/);
            expect(source).toMatch(/FALLBACK_RUNTIMES/);
            expect(source).toMatch(/runtimeOptions/);
        });

        it('should disable runtime select option when can_run is false and show reason', () => {
            expect(source).toMatch(/disabled=\{disabled\}/);
            expect(source).toMatch(/\.reason/);
        });

        it('should expose runtime/profile selectors and dry-run preflight', () => {
            expect(source).toMatch(/arc-studio-chat__runtime-selector/);
            expect(source).toMatch(/arc-studio-chat__profile-selector/);
            expect(source).toMatch(/arc-studio-chat__paid-calls/);
            expect(source).toMatch(/allowPaidCalls/);
            expect(source).toMatch(/arc-studio-chat__dry-run/);
            expect(source).toMatch(/preflightRun/);
            expect(source).toMatch(/arc-studio-chat__run/);
            expect(source).toMatch(/startRun/);
        });

        it('should show runtime readiness and keep local transcript', () => {
            expect(source).toMatch(/arc-studio-chat__runtime-readiness/);
            expect(source).toMatch(/selectedCapability/);
            expect(source).toMatch(/arc-studio-chat__transcript/);
            expect(source).toMatch(/setTranscript/);
        });

        it('should include CrewAI plus SwarmGraph fake offline option', () => {
            expect(source).toMatch(/crewai\+swarmgraph/);
            expect(source).toMatch(/CrewAI \+ SwarmGraph \(fake\/offline\)/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('RunsTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'RunsTab.tsx'), 'utf-8');
        });

        it('should export RunsTabProps interface', () => {
            expect(source).toMatch(/export interface RunsTabProps/);
        });

        it('should accept arcService prop', () => {
            expect(source).toMatch(/arcService:\s*ArcService/);
        });

        it('should have refresh button', () => {
            expect(source).toMatch(/arc-studio-runs__refresh/);
            expect(source).toMatch(/Refresh/);
        });

        it('should have placeholder', () => {
            expect(source).toMatch(/arc-studio-runs__placeholder/);
            expect(source).toMatch(/No runs yet/);
        });

        it('should have hint text', () => {
            expect(source).toMatch(/arc-studio-runs__hint/);
        });

        it('should have run list items with status badges', () => {
            expect(source).toMatch(/arc-studio-runs__item/);
            expect(source).toMatch(/arc-studio-runs__item-status/);
        });

        it('should have detail panel', () => {
            expect(source).toMatch(/arc-studio-runs__detail/);
            expect(source).toMatch(/arc-studio-runs__detail-placeholder/);
        });

        it('should import RunReceiptCard', () => {
            expect(source).toMatch(/RunReceiptCard/);
        });

        it('should import FailureAutopsyCard', () => {
            expect(source).toMatch(/FailureAutopsyCard/);
        });

        it('should import RunContractCard', () => {
            expect(source).toMatch(/RunContractCard/);
        });

        it('should use React.useState and React.useEffect', () => {
            expect(source).toMatch(/React\.useState/);
            expect(source).toMatch(/React\.useEffect/);
            expect(source).toMatch(/React\.useCallback/);
        });

        it('should call getTraces, getRunReceipt, getRunAutopsy, getRunContract', () => {
            expect(source).toMatch(/arcService\.getTraces/);
            expect(source).toMatch(/arcService\.getRunReceipt/);
            expect(source).toMatch(/arcService\.getRunAutopsy/);
            expect(source).toMatch(/arcService\.getRunContract/);
        });

        it('should expose run diff controls backed by ArcService.diffRuns', () => {
            expect(source).toMatch(/RunDiffResult/);
            expect(source).toMatch(/diffRunAId/);
            expect(source).toMatch(/diffRunBId/);
            expect(source).toMatch(/arcService\.diffRuns\(state\.diffRunAId, state\.diffRunBId\)/);
            expect(source).toMatch(/arc-studio-runs__diff-compare/);
            expect(source).toMatch(/JSON\.stringify\(diffResult, null, 2\)/);
            expect(source).not.toMatch(/fetch\(/);
            expect(source).not.toMatch(/arc-core/);
        });

        it('should render receipt card conditionally', () => {
            expect(source).toMatch(/receipt\s*&&\s*\(/);
            expect(source).toMatch(/<RunReceiptCard/);
        });

        it('should render autopsy card when available', () => {
            expect(source).toMatch(/autopsy/);
            expect(source).not.toMatch(/selectedRun\?\.status\s*===\s*'failed'/);
        });

        it('should tolerate missing run detail artifacts', () => {
            expect(source).toMatch(/getRunReceipt\(runId\)\.catch\(\(\) => null\)/);
            expect(source).toMatch(/getRunAutopsy\(runId\)\.catch\(\(\) => null\)/);
            expect(source).toMatch(/getRunContract\(runId\)\.catch\(\(\) => null\)/);
        });

        it('should render contract card conditionally', () => {
            expect(source).toMatch(/contract\s*&&\s*\(/);
            expect(source).toMatch(/<RunContractCard/);
        });

        it('should handle loading state', () => {
            expect(source).toMatch(/Loading runs…/);
            expect(source).toMatch(/Loading run details…/);
        });

        it('should handle error state', () => {
            expect(source).toMatch(/arc-studio-runs__error/);
        });

        it('should have layout container', () => {
            expect(source).toMatch(/arc-studio-runs__layout/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('WorkflowsTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'WorkflowsTab.tsx'), 'utf-8');
        });

        it('should export WorkflowsTabProps interface', () => {
            expect(source).toMatch(/export interface WorkflowsTabProps/);
        });

        it('should have workflows prop', () => {
            expect(source).toMatch(/workflows:\s*WorkflowInfo\[\]/);
        });

        it('should have isScanning prop', () => {
            expect(source).toMatch(/isScanning:\s*boolean/);
        });

        it('should have onScanWorkspace prop', () => {
            expect(source).toMatch(/onScanWorkspace/);
        });

        it('should have scan button', () => {
            expect(source).toMatch(/arc-studio-workflows__scan/);
            expect(source).toMatch(/Scan/);
        });

        it('should render workflow cards', () => {
            expect(source).toMatch(/arc-studio-workflows__card/);
        });

        it('should render workflow badges', () => {
            expect(source).toMatch(/arc-studio-workflows__badge/);
        });

        it('should have placeholder when no workflows', () => {
            expect(source).toMatch(/arc-studio-workflows__placeholder/);
            expect(source).toMatch(/No workflows detected/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('ConfigTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'ConfigTab.tsx'), 'utf-8');
        });

        it('should export ConfigTabProps interface', () => {
            expect(source).toMatch(/export interface ConfigTabProps/);
        });

        it('should have runtime radio group', () => {
            expect(source).toMatch(/type='radio'/);
            expect(source).toMatch(/name='runtime'/);
        });

        it('should have runtime display metadata for known runtimes', () => {
            expect(source).toMatch(/RUNTIME_DISPLAY/);
            expect(source).toMatch(/swarmgraph/);
            expect(source).toMatch(/langgraph/);
            expect(source).toMatch(/crewai/);
            expect(source).toMatch(/crewai\+swarmgraph/);
            expect(source).toMatch(/openai-agents/);
            expect(source).toMatch(/ag2/);
        });

        it('should load runtime capabilities from backend for disabled state', () => {
            expect(source).toMatch(/listRuntimeCapabilities/);
            expect(source).toMatch(/caps\.runtimes/);
        });

        it('should disable runtime radio when can_run is false', () => {
            expect(source).toMatch(/!opt\.canRun/);
            expect(source).toMatch(/disabled=\{disabled\}/);
        });

        it('should show capability-driven reason for disabled runtime', () => {
            expect(source).toMatch(/⛔/);
            expect(source).toMatch(/opt\.description/);
        });

        it('should have mode radio group', () => {
            expect(source).toMatch(/name='mode'/);
            expect(source).toMatch(/plan/);
            expect(source).toMatch(/build/);
            expect(source).toMatch(/auto/);
        });

        it('should have mode descriptions', () => {
            expect(source).toMatch(/read-only/);
            expect(source).toMatch(/edit/);
            expect(source).toMatch(/policy-driven/);
        });

        it('should have trust status', () => {
            expect(source).toMatch(/arc-studio-config__trusted/);
            expect(source).toMatch(/arc-studio-config__untrusted/);
            expect(source).toMatch(/Workspace.*trusted/);
        });

        it('should have save button', () => {
            expect(source).toMatch(/arc-studio-config__save/);
            expect(source).toMatch(/Save/);
        });

        it('should have providers section', () => {
            expect(source).toMatch(/Providers/);
        });

        it('should have provider dropdown and env var input', () => {
            expect(source).toMatch(/arc-studio-config__provider-dropdown/);
            expect(source).toMatch(/arc-studio-config__provider-env-input/);
            expect(source).toMatch(/OPENAI_API_KEY/);
        });

        it('should have save key reference button', () => {
            expect(source).toMatch(/Save key reference/);
            expect(source).toMatch(/setProviderKeyRef/);
        });

        it('should show web auth warning', () => {
            expect(source).toMatch(/Web session auth is research-only/);
            expect(source).toMatch(/does not capture browser cookies/);
        });

        it('should show provider source badges', () => {
            expect(source).toMatch(/keyring/);
            expect(source).toMatch(/env/);
            expect(source).toMatch(/unset/);
        });

        it('should show env override labels', () => {
            expect(source).toMatch(/arc-studio-config__env-override/);
            expect(source).toMatch(/envOverride/);
        });

        it('should display routing section', () => {
            expect(source).toMatch(/Routing/);
            expect(source).toMatch(/routingMode/);
            expect(source).toMatch(/dryRun/);
            expect(source).toMatch(/isolation/);
        });

        it('should handle unavailable backend gracefully', () => {
            expect(source).toMatch(/arc-studio-config__unavailable/);
            expect(source).toMatch(/Backend unavailable/);
            expect(source).toMatch(/Retry/);
        });

        it('should have config save method', () => {
            expect(source).toMatch(/handleSave/);
            expect(source).toMatch(/saveConfig/);
        });

        it('should NOT render raw api_key values', () => {
            expect(source).not.toMatch(/api_key[^_]/);
            expect(source).not.toMatch(/apiKey[^C]/);
            expect(source).not.toMatch(/secret/);
            expect(source).not.toMatch(/password/);
        });

        it('should show keys as source/status only', () => {
            expect(source).toMatch(/source\/status only/);
            expect(source).toMatch(/raw values are never displayed/);
        });

        it('should load config from backend', () => {
            expect(source).toMatch(/getConfigStatus/);
            expect(source).toMatch(/loadConfig/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });
});
