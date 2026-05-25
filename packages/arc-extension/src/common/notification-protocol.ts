/**
 * Notification protocol types for ARC Studio event badges (Phase 32 / R25).
 *
 * Provides TypeScript interfaces for notification counts consumed by
 * the IDE badge components.
 */

export interface NotificationCounts {
    hitl: number;
    runFailures: number;
    auditAlerts: number;
}

export const NotificationService = Symbol('NotificationService');

export const NotificationServicePath = '/services/arc/notifications';

export interface NotificationService {
    getCounts(): Promise<NotificationCounts>;
}
