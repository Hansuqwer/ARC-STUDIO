/**
 * Chat Tab
 *
 * Placeholder chat panel with input and mode indicator.
 */

import * as React from '@theia/core/shared/react';
import { useState } from '@theia/core/shared/react';

export interface ChatTabProps {
    onSendMessage?: (message: string) => void;
}

export const ChatTab: React.FC<ChatTabProps> = ({ onSendMessage }) => {
    const [input, setInput] = useState('');
    const [mode, setMode] = useState<'plan' | 'build' | 'auto'>('build');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;
        if (onSendMessage) {
            onSendMessage(input.trim());
        }
        setInput('');
    };

    const cycleMode = () => {
        const modes: Array<'plan' | 'build' | 'auto'> = ['plan', 'build', 'auto'];
        const idx = modes.indexOf(mode);
        setMode(modes[(idx + 1) % modes.length]);
    };

    return (
        <div className='arc-studio-chat' role='region' aria-label='Chat panel'>
            <div className='arc-studio-chat__header'>
                <span className='arc-studio-chat__mode' onClick={cycleMode} title='Click to cycle mode'>
                    Mode: {mode}
                </span>
            </div>

            <div className='arc-studio-chat__messages' aria-live='polite'>
                <div className='arc-studio-chat__placeholder'>
                    <p>Chat is ready. Type a message or use slash commands.</p>
                    <p className='arc-studio-chat__hint'>
                        Try: /help /config /runtime /status /workflows
                    </p>
                </div>
            </div>

            <form className='arc-studio-chat__input' onSubmit={handleSubmit}>
                <input
                    type='text'
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder='Type a message or /command...'
                    aria-label='Chat input'
                    className='arc-studio-chat__input-field'
                />
                <button
                    type='submit'
                    className='arc-studio-chat__send'
                    disabled={!input.trim()}
                    aria-label='Send message'
                >
                    Send
                </button>
            </form>
        </div>
    );
};
