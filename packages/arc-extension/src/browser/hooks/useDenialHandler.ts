import { useState } from 'react';

export interface DenialState {
    reason: string;
    correlationId: string;
}

export function useDenialHandler() {
    const [denial, setDenial] = useState<DenialState | null>(null);

    const handleDenial = (event: { event?: string; denial?: { message?: string; correlation_id?: string } }) => {
        if (event.event === 'denied' && event.denial) {
            setDenial({
                reason: event.denial.message ?? 'Operation denied by security gate',
                correlationId: event.denial.correlation_id ?? 'unknown',
            });
        }
    };

    const handleApprove = async (): Promise<boolean> => {
        if (!denial) {
            return false;
        }
        try {
            const response = await fetch('/api/enforcement/retry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    correlation_id: denial.correlationId,
                    user_approved: true,
                }),
            });
            const result = await response.json();
            setDenial(null);
            return result.proceed === true;
        } catch {
            setDenial(null);
            return false;
        }
    };

    const handleDecline = async (): Promise<boolean> => {
        if (!denial) {
            return false;
        }
        try {
            await fetch('/api/enforcement/retry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    correlation_id: denial.correlationId,
                    user_approved: false,
                }),
            });
        } catch {
            // Silently fail on decline — operation was already cancelled
        }
        setDenial(null);
        return false;
    };

    return {
        denial,
        handleDenial,
        handleApprove,
        handleDecline,
    } as const;
}
