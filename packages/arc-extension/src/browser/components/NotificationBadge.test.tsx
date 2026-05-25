/**
 * Tests for NotificationBadge component.
 */

import * as React from 'react';
import { render } from '@testing-library/react';
import { NotificationBadge } from './NotificationBadge';

describe('NotificationBadge', () => {
    it('renders nothing when count is 0', () => {
        const { container } = render(<NotificationBadge count={0} />);
        expect(container.querySelector('[data-testid="notification-badge"]')).toBeNull();
    });

    it('renders count 1', () => {
        const { getByTestId } = render(<NotificationBadge count={1} />);
        expect(getByTestId('notification-badge').textContent).toBe('1');
    });

    it('renders count 5', () => {
        const { getByTestId } = render(<NotificationBadge count={5} />);
        expect(getByTestId('notification-badge').textContent).toBe('5');
    });

    it('renders count 9', () => {
        const { getByTestId } = render(<NotificationBadge count={9} />);
        expect(getByTestId('notification-badge').textContent).toBe('9');
    });

    it('truncates 15 to 9+', () => {
        const { getByTestId } = render(<NotificationBadge count={15} />);
        expect(getByTestId('notification-badge').textContent).toBe('9+');
    });

    it('renders with failure variant', () => {
        const { getByTestId } = render(<NotificationBadge count={3} variant='failure' />);
        expect(getByTestId('notification-badge')).toBeTruthy();
        expect(getByTestId('notification-badge').textContent).toBe('3');
    });
});
