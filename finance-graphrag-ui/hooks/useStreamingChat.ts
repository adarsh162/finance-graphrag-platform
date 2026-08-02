// frontend/hooks/useStreamingChat.ts
import { useState, useRef, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';

export type Message = {
    role: 'user' | 'assistant';
    content: string;
    nodeUpdates?: string[];
};

export const useStreamingChat = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    
    const currentAssistantMessageRef = useRef<Message>({ role: 'assistant', content: '', nodeUpdates: [] });

    const sendMessage = useCallback(async (question: string, threadId: string) => {
        setMessages((prev) => [...prev, { role: 'user', content: question }]);
        setIsLoading(true);

        currentAssistantMessageRef.current = { role: 'assistant', content: '', nodeUpdates: [] };
        
        setMessages((prev) => [...prev, currentAssistantMessageRef.current]);

        try {
            await fetchEventSource('http://localhost:8000/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                },
                body: JSON.stringify({ question, thread_id: threadId }),
                
                onmessage(event) {
                    const data = JSON.parse(event.data);

                    if (data.type === 'node_update') {
                        currentAssistantMessageRef.current.nodeUpdates?.push(data.node);
                    } 
                    else if (data.type === 'token') {
                        currentAssistantMessageRef.current.content += data.content;
                    }
                    else if (data.type === 'done') {
                        setIsLoading(false);
                    }

                    setMessages((prev) => {
                        const newMessages = [...prev];
                        newMessages[newMessages.length - 1] = { ...currentAssistantMessageRef.current };
                        return newMessages;
                    });
                },
                onerror(err) {
                    console.error("SSE Connection Error:", err);
                    setIsLoading(false);
                    
                    // Display an explicit error message instead of leaving an empty bubble
                    setMessages((prev) => {
                        const newMessages = [...prev];
                        newMessages[newMessages.length - 1] = {
                            role: 'assistant',
                            content: '⚠️ Unable to connect to backend server. Make sure Docker and FastAPI are running.'
                        };
                        return newMessages;
                    });
                    
                    throw err; // Prevents fetchEventSource from endlessly retrying
                }
            });
        } catch (error) {
            console.error("Failed to stream chat:", error);
            setIsLoading(false);
        }
    }, []);

    return { messages, sendMessage, isLoading };
};