/**
 * Shortcuts Modal Component
 * 
 * Displays keyboard shortcuts help dialog.
 */

import * as React from '@theia/core/shared/react';

export interface ShortcutsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const ShortcutsModal: React.FC<ShortcutsModalProps> = ({ isOpen, onClose }) => {
    const modalRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        if (!isOpen) {
            return;
        }
        const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.[0]?.focus();
    }, [isOpen]);

    const trapFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === 'Escape') {
            onClose();
            return;
        }
        if (event.key !== 'Tab') {
            return;
        }
        const focusable = Array.from(
            modalRef.current?.querySelectorAll<HTMLElement>(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            ) || []
        );
        if (focusable.length === 0) {
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div 
            className='arc-modal-overlay' 
            role='dialog' 
            aria-modal='true' 
            aria-labelledby='shortcuts-title'
            onKeyDown={trapFocus}
            onClick={(e) => {
                if (e.target === e.currentTarget) {
                    onClose();
                }
            }}
        >
            <div className='arc-modal' ref={modalRef}>
                <div className='arc-modal-header'>
                    <h3 id='shortcuts-title'>Keyboard Shortcuts</h3>
                    <button 
                        className='arc-modal-close'
                        onClick={onClose}
                        aria-label='Close shortcuts help'
                    >
                        ×
                    </button>
                </div>
                <div className='arc-modal-content'>
                    <table className='arc-shortcuts-table'>
                        <thead>
                            <tr>
                                <th>Action</th>
                                <th>Windows/Linux</th>
                                <th>Mac</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Execute Workflow</td>
                                <td><kbd>Ctrl+E</kbd></td>
                                <td><kbd>⌘+E</kbd></td>
                            </tr>
                            <tr>
                                <td>Load Traces</td>
                                <td><kbd>Ctrl+L</kbd></td>
                                <td><kbd>⌘+L</kbd></td>
                            </tr>
                            <tr>
                                <td>Scan Workspace</td>
                                <td><kbd>Ctrl+S</kbd></td>
                                <td><kbd>⌘+S</kbd></td>
                            </tr>
                            <tr>
                                <td>Show Shortcuts</td>
                                <td><kbd>Ctrl+H</kbd></td>
                                <td><kbd>⌘+H</kbd></td>
                            </tr>
                            <tr>
                                <td>Close Modal</td>
                                <td><kbd>Esc</kbd></td>
                                <td><kbd>Esc</kbd></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
