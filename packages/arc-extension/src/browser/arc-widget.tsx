/**
 * ARC Widget
 * 
 * Main UI widget for ARC Studio showing workflow execution,
 * trace visualization, and SwarmGraph controls.
 */

import { injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import * as React from '@theia/core/shared/react';

@injectable()
export class ArcWidget extends ReactWidget {

    static readonly ID = 'arc-widget';
    static readonly LABEL = 'ARC Studio';

    @postConstruct()
    protected init(): void {
        this.id = ArcWidget.ID;
        this.title.label = ArcWidget.LABEL;
        this.title.caption = ArcWidget.LABEL;
        this.title.closable = true;
        this.title.iconClass = 'fa fa-project-diagram';
        this.update();
    }

    protected render(): React.ReactNode {
        return (
            <div className='arc-widget-container'>
                <div className='arc-header'>
                    <h2>ARC Studio</h2>
                    <p>Agent Runtime Cockpit</p>
                </div>
                <div className='arc-content'>
                    <div className='arc-section'>
                        <h3>Workflow Execution</h3>
                        <p>Execute SwarmGraph and LangGraph workflows</p>
                        <button className='theia-button'>Execute Workflow</button>
                    </div>
                    <div className='arc-section'>
                        <h3>Trace Viewer</h3>
                        <p>View execution traces from .arc/traces/</p>
                        <button className='theia-button'>Load Traces</button>
                    </div>
                    <div className='arc-section'>
                        <h3>Workflow Detection</h3>
                        <p>Detect workflows in workspace</p>
                        <button className='theia-button'>Scan Workspace</button>
                    </div>
                </div>
            </div>
        );
    }
}
