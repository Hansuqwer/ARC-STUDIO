import * as React from '@theia/core/shared/react';

export interface DenialModalProps {
    isOpen: boolean;
    denialReason: string;
    correlationId: string;
    onApprove: () => void;
    onDecline: () => void;
}

export const DenialModal: React.FC<DenialModalProps> = ({
    isOpen,
    denialReason,
    correlationId,
    onApprove,
    onDecline,
}) => {
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
            onDecline();
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
            aria-labelledby='denial-title'
            onKeyDown={trapFocus}
            onClick={(e) => {
                if (e.target === e.currentTarget) {
                    onDecline();
                }
            }}
        >
            <div className='arc-modal' ref={modalRef}>
                <div className='arc-modal-header'>
                    <h3 id='denial-title'>Security Gate</h3>
                    <button
                        className='arc-modal-close'
                        onClick={onDecline}
                        aria-label='Close security gate dialog'
                    >
                        ×
                    </button>
                </div>
                <div className='arc-modal-content'>
                    <p>{denialReason}</p>
                    <div className='arc-denial-correlation-id'>
                        ID: {correlationId}
                    </div>
                </div>
                <div className='arc-modal-footer'>
                    <button
                        className='theia-button secondary'
                        onClick={onDecline}
                        aria-label='Decline and cancel operation'
                    >
                        Decline
                    </button>
                    <button
                        className='theia-button primary'
                        onClick={onApprove}
                        aria-label='Approve and proceed'
                    >
                        Approve
                    </button>
                </div>
            </div>
        </div>
    );
};
