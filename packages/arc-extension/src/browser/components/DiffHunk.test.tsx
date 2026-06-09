/**
 * Phase 292 — R89b: DiffHunk accept/reject component tests.
 */

import * as React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { DiffHunk } from '../components/DiffHunk';

const SAMPLE_HUNK = `@@ -1,3 +1,3 @@
 context line
-old line
+new line
 context line`;

describe('DiffHunk', () => {
    it('renders hunk content', () => {
        render(<DiffHunk index={1} total={3} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={jest.fn()} />);
        expect(screen.getByText(/old line/)).toBeTruthy();
        expect(screen.getByText(/new line/)).toBeTruthy();
    });

    it('shows counter 1 / 3', () => {
        render(<DiffHunk index={1} total={3} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={jest.fn()} />);
        expect(screen.getByText('1 / 3')).toBeTruthy();
    });

    it('calls onAccept with index when Accept clicked', () => {
        const onAccept = jest.fn();
        render(<DiffHunk index={2} total={3} hunk={SAMPLE_HUNK}
            onAccept={onAccept} onReject={jest.fn()} />);
        fireEvent.click(screen.getByRole('button', { name: /Accept hunk 2/i }));
        expect(onAccept).toHaveBeenCalledWith(2);
    });

    it('calls onReject with index when Reject clicked', () => {
        const onReject = jest.fn();
        render(<DiffHunk index={1} total={1} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={onReject} />);
        fireEvent.click(screen.getByRole('button', { name: /Reject hunk 1/i }));
        expect(onReject).toHaveBeenCalledWith(1);
    });

    it('hides action buttons when decision=accepted', () => {
        render(<DiffHunk index={1} total={1} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={jest.fn()} decision='accepted' />);
        expect(screen.queryByRole('button')).toBeNull();
        expect(screen.getByText(/Accepted/i)).toBeTruthy();
    });

    it('hides action buttons when decision=rejected', () => {
        render(<DiffHunk index={1} total={1} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={jest.fn()} decision='rejected' />);
        expect(screen.queryByRole('button')).toBeNull();
        expect(screen.getByText(/Rejected/i)).toBeTruthy();
    });

    it('has accessible aria-labels on buttons', () => {
        render(<DiffHunk index={3} total={5} hunk={SAMPLE_HUNK}
            onAccept={jest.fn()} onReject={jest.fn()} />);
        expect(screen.getByLabelText(/Accept hunk 3/i)).toBeTruthy();
        expect(screen.getByLabelText(/Reject hunk 3/i)).toBeTruthy();
    });
});
