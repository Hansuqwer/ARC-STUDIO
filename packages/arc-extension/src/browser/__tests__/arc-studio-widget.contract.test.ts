/**
 * ArcStudioWidget Contract Tests
 *
 * Static source-pattern tests for the Studio widget, contribution, and frontend module binding.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ArcStudioWidget Contracts', () => {
    const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');
    let widgetSource: string;

    beforeAll(async () => {
        widgetSource = await fs.readFile(path.join(browserDir, 'arc-studio-widget.tsx'), 'utf-8');
    });

    describe('Static Properties', () => {
        it('should have correct ID', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+ID\s*=\s*['"]arc-studio-widget['"]/);
        });

        it('should have correct LABEL', () => {
            expect(widgetSource).toMatch(/static\s+readonly\s+LABEL\s*=\s*['"]ARC Studio['"]/);
        });
    });

    describe('Class Structure', () => {
        it('should be an injectable class', () => {
            expect(widgetSource).toMatch(/@injectable\(\)/);
            expect(widgetSource).toMatch(/export\s+class\s+ArcStudioWidget/);
        });

        it('should extend ReactWidget', () => {
            expect(widgetSource).toMatch(/class\s+ArcStudioWidget\s+extends\s+ReactWidget/);
        });

        it('should have a render method', () => {
            expect(widgetSource).toMatch(/protected\s+render\s*\(\s*\)\s*:\s*React\.ReactNode/);
        });

        it('should have an init method with postConstruct', () => {
            expect(widgetSource).toMatch(/@postConstruct\(\)/);
            expect(widgetSource).toMatch(/protected\s+init\s*\(\s*\)/);
        });

        it('should inject ArcService', () => {
            expect(widgetSource).toMatch(/@inject\(ArcService\)/);
        });
    });

    describe('Tab Rendering', () => {
        it('should import ChatTab', () => {
            expect(widgetSource).toMatch(/import.*ChatTab.*from.*tabs/);
        });

        it('should import RunsTab', () => {
            expect(widgetSource).toMatch(/import.*RunsTab.*from.*tabs/);
        });

        it('should import WorkflowsTab', () => {
            expect(widgetSource).toMatch(/import.*WorkflowsTab.*from.*tabs/);
        });

        it('should import ConfigTab', () => {
            expect(widgetSource).toMatch(/import.*ConfigTab.*from.*tabs/);
        });

        it('should render ChatTab in render', () => {
            expect(widgetSource).toMatch(/<ChatTab/);
        });

        it('should render RunsTab in render', () => {
            expect(widgetSource).toMatch(/<RunsTab/);
        });

        it('should render WorkflowsTab in render', () => {
            expect(widgetSource).toMatch(/<WorkflowsTab/);
        });

        it('should render ConfigTab in render', () => {
            expect(widgetSource).toMatch(/<ConfigTab/);
        });

        it('should pass arcService prop to ConfigTab', () => {
            expect(widgetSource).toMatch(/<ConfigTab\s+arcService=\{this\.arcService\}/);
        });

        it('should pass arcService prop to RunsTab', () => {
            expect(widgetSource).toMatch(/<RunsTab\s+arcService=\{this\.arcService\}/);
        });
    });

    describe('NO TraceViewerSection', () => {
        it('should NOT import TraceViewerSection', () => {
            expect(widgetSource).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('Tab Bar', () => {
        it('should render tablist', () => {
            expect(widgetSource).toMatch(/role='tablist'/);
        });

        it('should render tab buttons', () => {
            expect(widgetSource).toMatch(/role='tab'/);
        });

        it('should have aria-selected on tabs', () => {
            expect(widgetSource).toMatch(/aria-selected/);
        });

        it('should have tab panels', () => {
            expect(widgetSource).toMatch(/role='tabpanel'/);
        });

        it('should have 4 tabs: Chat, Runs, Workflows, Config', () => {
            expect(widgetSource).toMatch(/Chat/);
            expect(widgetSource).toMatch(/Runs/);
            expect(widgetSource).toMatch(/Workflows/);
            expect(widgetSource).toMatch(/Config/);
        });
    });

    describe('Status Strip', () => {
        it('should render status strip', () => {
            expect(widgetSource).toMatch(/arc-studio-status/);
            expect(widgetSource).toMatch(/role='status'/);
        });

        it('should show runtime segment', () => {
            expect(widgetSource).toMatch(/Runtime:\s*\{runtime\}/);
        });

        it('should show model segment', () => {
            expect(widgetSource).toMatch(/Model:\s*unset/);
        });

        it('should show mode segment', () => {
            expect(widgetSource).toMatch(/Mode:\s*\{mode\}/);
        });

        it('should show workspace segment', () => {
            expect(widgetSource).toMatch(/Workspace:\s*\{workspaceTrust\}/);
            expect(widgetSource).not.toMatch(/Workspace:\s*trusted/);
        });

        it('should load status from ArcService', () => {
            expect(widgetSource).toMatch(/getConfigStatus/);
            expect(widgetSource).toMatch(/workspace\.trustLevel/);
        });
    });

    describe('Widget Initialization', () => {
        it('should set widget ID in init', () => {
            expect(widgetSource).toMatch(/this\.id\s*=\s*ArcStudioWidget\.ID/);
        });

        it('should set title label in init', () => {
            expect(widgetSource).toMatch(/this\.title\.label\s*=\s*ArcStudioWidget\.LABEL/);
        });

        it('should make widget closable', () => {
            expect(widgetSource).toMatch(/this\.title\.closable\s*=\s*true/);
        });
    });
});

describe('ArcStudioWidgetContribution', () => {
    const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(browserDir, 'arc-studio-widget-contribution.ts'), 'utf-8');
    });

    it('should be injectable', () => {
        expect(source).toMatch(/@injectable/);
    });

    it('should extend AbstractViewContribution', () => {
        expect(source).toMatch(/extends AbstractViewContribution/);
    });

    it('should have arc-studio:open command', () => {
        expect(source).toMatch(/arc-studio:open/);
    });

    it('should have rank 90 (before legacy widget)', () => {
        expect(source).toMatch(/rank:\s*90/);
    });

    it('should reference ArcStudioWidget.ID', () => {
        expect(source).toMatch(/ArcStudioWidget\.ID/);
    });

    it('should reference ArcStudioWidget.LABEL', () => {
        expect(source).toMatch(/ArcStudioWidget\.LABEL/);
    });
});

describe('Frontend Module Binding', () => {
    const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(path.join(browserDir, 'arc-extension-frontend-module.ts'), 'utf-8');
    });

    it('should import ArcStudioWidget', () => {
        expect(source).toMatch(/import.*ArcStudioWidget.*from.*arc-studio-widget/);
    });

    it('should import ArcStudioWidgetContribution', () => {
        expect(source).toMatch(/import.*ArcStudioWidgetContribution.*from.*arc-studio-widget-contribution/);
    });

    it('should bind ArcStudioWidget', () => {
        expect(source).toMatch(/bind\(ArcStudioWidget\)/);
    });

    it('should bind ArcStudioWidgetContribution', () => {
        expect(source).toMatch(/bindViewContribution\(bind,\s*ArcStudioWidgetContribution\)/);
    });

    it('should register WidgetFactory for ArcStudioWidget', () => {
        expect(source).toMatch(/id:\s*ArcStudioWidget\.ID/);
    });

    it('should import arc-studio-widget.css', () => {
        expect(source).toMatch(/arc-studio-widget\.css/);
    });
});
