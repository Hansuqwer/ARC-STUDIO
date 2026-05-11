/**
 * ARC Schema Inspector Widget
 * Displays JSON schemas for all detected runtime state models.
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { SchemaInfo } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcSchemaInspectorWidget extends ReactWidget {
  static readonly ID = 'arc:schema-inspector';
  static readonly LABEL = 'ARC Schema Inspector';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected schemas: SchemaInfo[] = [];
  protected selected: SchemaInfo | null = null;
  protected loading = false;

  @postConstruct()
  protected init(): void {
    this.id = ArcSchemaInspectorWidget.ID;
    this.title.label = ArcSchemaInspectorWidget.LABEL;
    this.title.closable = true;
    this.loadSchemas();
  }

  protected async loadSchemas(): Promise<void> {
    this.loading = true;
    this.update();
    try {
      const result = await this.arcService.listSchemas();
      this.schemas = result.data ?? [];
      if (this.schemas.length > 0) this.selected = this.schemas[0];
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected render(): React.ReactNode {
    if (this.loading) {
      return <div style={{ padding: 24, textAlign: 'center' }}>Loading schemas…</div>;
    }

    return (
      <div style={{ display: 'flex', height: '100%', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)' }}>
        {/* Schema List */}
        <div style={{ width: '220px', borderRight: '1px solid var(--theia-widget-border)', overflow: 'auto', flexShrink: 0 }}>
          <div style={{ padding: '8px 12px', fontWeight: 600, borderBottom: '1px solid var(--theia-widget-border)', fontSize: '12px' }}>
            Schemas ({this.schemas.length})
          </div>
          {this.schemas.map(s => (
            <div
              key={s.id}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                backgroundColor: this.selected?.id === s.id ? 'var(--theia-list-activeSelectionBackground)' : 'transparent',
                color: this.selected?.id === s.id ? 'var(--theia-list-activeSelectionForeground)' : 'inherit',
                borderBottom: '1px solid var(--theia-widget-border)',
              }}
              onClick={() => { this.selected = s; this.update(); }}
            >
              <div style={{ fontWeight: 500, fontSize: '12px' }}>{s.name}</div>
              <div style={{ fontSize: '10px', opacity: 0.7 }}>{s.runtime}</div>
            </div>
          ))}
          {this.schemas.length === 0 && (
            <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--theia-descriptionForeground)', fontSize: '12px' }}>
              No schemas found
            </div>
          )}
        </div>

        {/* Schema Detail */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          {this.selected ? (
            <div>
              <h2 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>{this.selected.name}</h2>
              <div style={{ marginBottom: '12px', fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                Runtime: <strong>{this.selected.runtime}</strong>
                {this.selected.source_file && (
                  <span> · <code style={{ fontSize: '11px' }}>{this.selected.source_file}</code></span>
                )}
              </div>
              {this.selected.schema?.description && (
                <div style={{ marginBottom: '12px', fontSize: '12px', padding: '8px', backgroundColor: 'var(--theia-textBlockQuote-background)', borderRadius: '4px' }}>
                  {String(this.selected.schema.description)}
                </div>
              )}
              <h3 style={{ margin: '0 0 8px 0', fontSize: '13px' }}>Properties</h3>
              {this.renderProperties(this.selected.schema)}
              <h3 style={{ margin: '16px 0 8px 0', fontSize: '13px' }}>Raw JSON Schema</h3>
              <pre style={{
                fontSize: '11px',
                backgroundColor: 'var(--theia-textCodeBlock-background)',
                padding: '12px',
                borderRadius: '6px',
                overflow: 'auto',
                maxHeight: '400px',
                margin: 0,
              }}>
                {JSON.stringify(this.selected.schema, null, 2)}
              </pre>
            </div>
          ) : (
            <div style={{ textAlign: 'center', paddingTop: '48px', color: 'var(--theia-descriptionForeground)' }}>
              Select a schema to inspect
            </div>
          )}
        </div>
      </div>
    );
  }

  protected renderProperties(schema: Record<string, unknown>): React.ReactNode {
    const props = schema?.properties as Record<string, Record<string, unknown>> | undefined;
    if (!props) return <div style={{ fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>No properties defined</div>;

    const required = (schema.required as string[]) ?? [];

    return (
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--theia-widget-border)' }}>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>Type</th>
            <th style={thStyle}>Required</th>
            <th style={thStyle}>Description</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(props).map(([name, def]) => (
            <tr key={name} style={{ borderBottom: '1px solid var(--theia-widget-border)' }}>
              <td style={tdStyle}><code>{name}</code></td>
              <td style={tdStyle}>{String(def.type ?? 'any')}</td>
              <td style={tdStyle}>{required.includes(name) ? '✓' : '—'}</td>
              <td style={{ ...tdStyle, color: 'var(--theia-descriptionForeground)' }}>
                {String(def.description ?? '')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
}

const thStyle: React.CSSProperties = {
  padding: '6px 8px',
  textAlign: 'left',
  fontWeight: 600,
  color: 'var(--theia-descriptionForeground)',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 8px',
};
