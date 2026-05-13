/**
 * Toast Notification Component
 * 
 * Displays toast notifications with auto-dismiss.
 */

import * as React from '@theia/core/shared/react';

export interface ToastNotification {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    message: string;
    timestamp: number;
}

export interface ToastContainerProps {
    toasts: ToastNotification[];
    onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
    return (
        <div className='arc-toast-container' role='region' aria-label='Notifications' aria-live='polite'>
            {toasts.map((toast: ToastNotification) => (
                <div 
                    key={toast.id} 
                    className={`arc-toast arc-toast-${toast.type}`}
                    role='alert'
                    aria-atomic='true'
                >
                    <span className='arc-toast-icon' aria-hidden='true'>
                        {toast.type === 'success' && '✓'}
                        {toast.type === 'error' && '✗'}
                        {toast.type === 'info' && 'ℹ'}
                        {toast.type === 'warning' && '⚠'}
                    </span>
                    <span className='arc-toast-message'>{toast.message}</span>
                    <button 
                        className='arc-toast-dismiss'
                        onClick={() => onDismiss(toast.id)}
                        aria-label='Dismiss notification'
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
};
