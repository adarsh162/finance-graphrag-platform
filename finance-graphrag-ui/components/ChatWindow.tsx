// frontend/components/ChatWindow.tsx
'use client';

import { useState } from 'react';
import { useStreamingChat } from '../hooks/useStreamingChat';

export default function ChatWindow() {
    const [input, setInput] = useState('');
    const threadId = "finance_session_01"; 
    
    const { messages, sendMessage, isLoading } = useStreamingChat();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;
        
        sendMessage(input, threadId);
        setInput('');
    };

    return (
        <div className="flex flex-col h-[600px] w-full max-w-3xl mx-auto border rounded-lg p-4 bg-white shadow-sm">
            {/* Message Display Area */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4 p-2">
                {messages.map((msg, idx) => {
                    const isLastMessage = idx === messages.length - 1;
                    const isAssistant = msg.role === 'assistant';
                    
                    // Hide empty assistant bubbles when not actively loading
                    if (isAssistant && !msg.content && !isLoading && !isLastMessage) {
                        return null;
                    }

                    return (
                        <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                            
                            {/* System Event Indicator */}
                            {isAssistant && msg.nodeUpdates && msg.nodeUpdates.length > 0 && (
                                <div className="text-xs text-blue-600 font-mono mb-1">
                                    ⚙️ Step: {msg.nodeUpdates[msg.nodeUpdates.length - 1]}
                                </div>
                            )}
                            
                            {/* Message Bubble */}
                            <div className={`p-3 rounded-lg max-w-[80%] text-sm ${
                                msg.role === 'user' 
                                    ? 'bg-blue-600 text-white' 
                                    : 'bg-gray-100 text-gray-800 border border-gray-200'
                            }`}>
                                {msg.content}
                                
                                {/* Pulsing cursor while waiting for tokens */}
                                {isLoading && isAssistant && isLastMessage && (
                                    <span className="inline-block w-1.5 h-4 ml-1 bg-gray-600 animate-pulse align-middle" />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a question about the SEC filings..."
                    className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800 text-sm"
                    disabled={isLoading}
                />
                <button 
                    type="submit" 
                    disabled={isLoading || !input.trim()}
                    className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50 text-sm"
                >
                    {isLoading ? 'Thinking...' : 'Send'}
                </button>
            </form>
        </div>
    );
}