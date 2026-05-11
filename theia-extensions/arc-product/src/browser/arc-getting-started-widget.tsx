/**
 * ARC Studio — Getting Started / Welcome Widget
 *
 * Replaces Theia's default welcome page with ARC Studio branding.
 * Source: https://theia-ide.org/docs/blueprint_documentation/#customizing-the-welcome-page
 * Source: https://github.com/eclipse-theia/theia-ide theia-blueprint-getting-started-widget.tsx
 */

import * as React from 'react';
import { injectable, inject } from '@theia/core/shared/inversify';
import { GettingStartedWidget } from '@theia/getting-started/lib/browser/getting-started-widget';
import { WorkspaceService } from '@theia/workspace/lib/browser/workspace-service';
import { ApplicationServer } from '@theia/core/lib/common/application-protocol';
import { EnvVariablesServer } from '@theia/core/lib/common/env-variables';
import { CommandService } from '@theia/core/lib/common/command';
import { FrontendApplicationStateService } from '@theia/core/lib/browser/frontend-application-state';
import { PreferenceService } from '@theia/core/lib/browser/preferences/preference-service';
import { WindowService } from '@theia/core/lib/browser/window/window-service';

export const ARC_STUDIO_VERSION = '0.1.0-alpha';

@injectable()
export class ArcGettingStartedWidget extends GettingStartedWidget {

  static override readonly ID = GettingStartedWidget.ID;
  static override readonly LABEL = 'Welcome to ARC Studio';

  protected override render(): React.ReactNode {
    return (
      <div className="arc-getting-started-container" style={styles.container}>
        <div style={styles.header}>
          <div style={styles.logo}>⬡</div>
          <h1 style={styles.title}>ARC Studio</h1>
          <p style={styles.subtitle}>Agent Runtime Cockpit IDE</p>
          <span style={styles.version}>v{ARC_STUDIO_VERSION}</span>
        </div>

        <div style={styles.grid}>
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>🚀 Get Started</h2>
            <ul style={styles.list}>
              <li style={styles.listItem}>
                <span style={styles.listIcon}>📂</span>
                Open a workspace containing an agent project
              </li>
              <li style={styles.listItem}>
                <span style={styles.listIcon}>🔍</span>
                Open the ARC panel from the Activity Bar (left)
              </li>
              <li style={styles.listItem}>
                <span style={styles.listIcon}>▶</span>
                Inspect, run, trace, and audit your agents
              </li>
            </ul>
          </section>

          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>🔌 Supported Runtimes</h2>
            <ul style={styles.list}>
              <li style={styles.listItem}><span style={styles.badge}>alpha</span> SwarmGraph</li>
              <li style={styles.listItem}><span style={styles.badge}>alpha</span> LangGraph</li>
              <li style={styles.listItem}><span style={styles.badgeGray}>planned</span> CrewAI</li>
              <li style={styles.listItem}><span style={styles.badgeGray}>planned</span> OpenAI Agents SDK</li>
              <li style={styles.listItem}><span style={styles.badgeGray}>planned</span> AG2</li>
            </ul>
          </section>

          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>📖 Documentation</h2>
            <ul style={styles.list}>
              <li style={styles.listItem}>
                <code style={styles.code}>docs/DEVELOPMENT.md</code> — Dev guide
              </li>
              <li style={styles.listItem}>
                <code style={styles.code}>docs/ARCHITECTURE.md</code> — Architecture
              </li>
              <li style={styles.listItem}>
                <code style={styles.code}>docs/EXTENSIONS.md</code> — Extension guide
              </li>
            </ul>
          </section>

          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>⚡ Quick Commands</h2>
            <ul style={styles.list}>
              <li style={styles.listItem}>
                <kbd style={styles.kbd}>F1</kbd> → "ARC: Inspect Workspace"
              </li>
              <li style={styles.listItem}>
                <kbd style={styles.kbd}>F1</kbd> → "ARC: List Runtimes"
              </li>
              <li style={styles.listItem}>
                <kbd style={styles.kbd}>F1</kbd> → "ARC: Open Workflow Graph"
              </li>
              <li style={styles.listItem}>
                <kbd style={styles.kbd}>F1</kbd> → "ARC: Start Run"
              </li>
            </ul>
          </section>
        </div>

        <footer style={styles.footer}>
          <p style={styles.footerText}>
            ARC Studio is built on{' '}
            <a href="https://theia-ide.org" style={styles.link}>Eclipse Theia</a>
            {' '}· Licensed under Apache 2.0
          </p>
          <p style={styles.footerText}>
            Python daemon: <code style={styles.code}>uv run arc serve</code>
          </p>
        </footer>
      </div>
    );
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: 'var(--theia-ui-font-family)',
    color: 'var(--theia-foreground)',
    backgroundColor: 'var(--theia-editor-background)',
    padding: '32px',
    height: '100%',
    overflowY: 'auto',
    boxSizing: 'border-box',
  },
  header: {
    textAlign: 'center',
    marginBottom: '40px',
    borderBottom: '1px solid var(--theia-widget-border)',
    paddingBottom: '24px',
  },
  logo: {
    fontSize: '64px',
    lineHeight: 1,
    marginBottom: '12px',
    color: '#4fc3f7',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: 700,
    margin: '0 0 8px 0',
    color: 'var(--theia-titleBar-activeForeground)',
  },
  subtitle: {
    fontSize: '1.1rem',
    color: 'var(--theia-descriptionForeground)',
    margin: '0 0 8px 0',
  },
  version: {
    fontSize: '0.8rem',
    color: 'var(--theia-descriptionForeground)',
    backgroundColor: 'var(--theia-badge-background)',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '24px',
    marginBottom: '40px',
  },
  section: {
    backgroundColor: 'var(--theia-sideBar-background)',
    borderRadius: '8px',
    padding: '20px',
    border: '1px solid var(--theia-widget-border)',
  },
  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    margin: '0 0 16px 0',
    color: 'var(--theia-foreground)',
  },
  list: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  listItem: {
    padding: '6px 0',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.9rem',
    color: 'var(--theia-descriptionForeground)',
  },
  listIcon: {
    fontSize: '16px',
  },
  badge: {
    backgroundColor: '#4fc3f7',
    color: '#000',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 600,
    flexShrink: 0,
  },
  badgeGray: {
    backgroundColor: 'var(--theia-badge-background)',
    color: 'var(--theia-badge-foreground)',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 600,
    flexShrink: 0,
  },
  code: {
    fontFamily: 'var(--theia-code-font-family)',
    backgroundColor: 'var(--theia-textCodeBlock-background)',
    padding: '1px 4px',
    borderRadius: '3px',
    fontSize: '0.85em',
  },
  kbd: {
    backgroundColor: 'var(--theia-keybindingLabel-background)',
    border: '1px solid var(--theia-keybindingLabel-border)',
    borderRadius: '3px',
    padding: '2px 6px',
    fontSize: '0.8rem',
    flexShrink: 0,
  },
  footer: {
    borderTop: '1px solid var(--theia-widget-border)',
    paddingTop: '16px',
    textAlign: 'center',
  },
  footerText: {
    fontSize: '0.85rem',
    color: 'var(--theia-descriptionForeground)',
    margin: '4px 0',
  },
  link: {
    color: 'var(--theia-textLink-foreground)',
    textDecoration: 'none',
  },
};
