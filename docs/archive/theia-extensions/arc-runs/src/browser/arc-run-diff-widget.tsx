/** ARC Run Diff Widget */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { RunRecord } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcRunDiffWidget extends ReactWidget {
  static readonly ID = 'arc:run-diff';
  static readonly LABEL = 'ARC Run Diff';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected runs: RunRecord[] = [];
  protected runAId = '';
  protected runBId = '';
  protected diffResult: string | null = null;
  protected loading = false;
  protected lastError?: string;

  @postConstruct()
  protected init(): void {
    this.id = ArcRunDiffWidget.ID;
    this.title.label = ArcRunDiffWidget.LABEL;
    this.title.closable = true;
    this.loadRuns();
  }

  protected async loadRuns(): Promise<void> {
    try {
      const result = await this.arcService.listRuns();
      this.runs = result.data ?? [];
    } catch (error) {
      this.lastError = String(error);
    }
    this.update();
  }

  protected render(): React.ReactNode {
    return (
      <div style={{ padding: 16, fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', height: '100%', overflow: 'auto' }}>
        <h2 style={{ margin: '0 0 12px', fontSize: 15 }}>Compare Runs</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
          <select
            style={selectStyle}
            value={this.runAId}
            onChange={e => { this.runAId = e.currentTarget.value; this.update(); }}
          >
            <option value="">Select Run A</option>
            {this.runs.map(run => (
              <option key={run.id} value={run.id}>{run.id.substring(0, 12)} ({run.status})</option>
            ))}
          </select>
          <select
            style={selectStyle}
            value={this.runBId}
            onChange={e => { this.runBId = e.currentTarget.value; this.update(); }}
          >
            <option value="">Select Run B</option>
            {this.runs.map(run => (
              <option key={run.id} value={run.id}>{run.id.substring(0, 12)} ({run.status})</option>
            ))}
          </select>
          <button
            style={primaryBtnStyle}
            disabled={!this.runAId || !this.runBId || this.loading}
            onClick={() => this.runDiff()}
            aria-label="Compare selected runs"
          >
            {this.loading ? 'Diffing...' : 'Diff'}
          </button>
          <button style={refreshBtnStyle} onClick={() => this.loadRuns()} aria-label="Refresh run list">Refresh</button>
        </div>
        {this.lastError && <div style={{ color: 'var(--theia-editorWarning-foreground)', fontSize: 11 }} role="alert">{this.lastError}</div>}
        {this.diffResult && <pre style={diffStyle} role="region" aria-label="Diff output">{this.diffResult}</pre>}
      </div>
    );
  }

  protected async runDiff(): Promise<void> {
    this.loading = true;
    this.lastError = undefined;
    this.diffResult = null;
    this.update();
    try {
      const response = await fetch(`http://127.0.0.1:7777/api/runs/diff?run_a=${this.runAId}&run_b=${this.runBId}`);
      const body = await response.json();
      if (body.data) {
        this.diffResult = JSON.stringify(body.data, null, 2);
      } else {
        this.lastError = body.error?.message ?? 'Diff failed';
      }
    } catch (error) {
      this.lastError = String(error);
    } finally {
      this.loading = false;
      this.update();
    }
  }
}

const selectStyle: React.CSSProperties = {
  flex: 1,
  color: 'var(--theia-input-foreground)',
  backgroundColor: 'var(--theia-input-background)',
  border: '1px solid var(--theia-input-border)',
  borderRadius: 4,
  padding: '4px 6px',
  fontSize: 12,
};

const primaryBtnStyle: React.CSSProperties = {
  padding: '6px 12px',
  color: 'var(--theia-button-foreground)',
  backgroundColor: 'var(--theia-button-background)',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
};

const refreshBtnStyle: React.CSSProperties = {
  padding: '6px 12px',
  color: 'var(--theia-secondaryButton-foreground)',
  backgroundColor: 'var(--theia-secondaryButton-background)',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
};

const diffStyle: React.CSSProperties = {
  marginTop: 8,
  padding: 12,
  backgroundColor: 'var(--theia-textCodeBlock-background)',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: 4,
  fontSize: 11,
  whiteSpace: 'pre-wrap',
  maxHeight: '80vh',
  overflow: 'auto',
};
