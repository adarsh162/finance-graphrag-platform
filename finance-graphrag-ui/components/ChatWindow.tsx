"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatWindow() {
  const [threadId] = useState(() => `session-${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: textToSend };
    
    // 🛑 1. Add user message AND the empty assistant placeholder immediately
    setMessages((prev) => [
      ...prev, 
      userMessage, 
      { role: "assistant", content: "" }
    ]);
    
    if (!queryText) setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question: textToSend, 
          thread_id: threadId 
        }), 
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error("🚨 FastAPI Error:", errorData);
        throw new Error("Chat request failed");
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace(/^data: /, '').trim();
            if (!dataStr || dataStr === '[DONE]') continue;
            
            try {
              const parsed = JSON.parse(dataStr);
              
              if (parsed.event && parsed.event !== "on_chat_model_stream") {
                continue; 
              }

              const textChunk = 
                parsed.content || 
                parsed.chunk || 
                parsed.data?.chunk?.content || 
                ""; 
              
              if (textChunk) {
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastIndex = newMessages.length - 1;
                  
                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    content: newMessages[lastIndex].content + textChunk
                  };
                  
                  return newMessages;
                });
              }
            } catch (e) {
              console.warn("Failed to parse stream chunk:", dataStr);
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        if (newMessages[lastIndex]?.role === "assistant" && !newMessages[lastIndex].content) {
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: "⚠️ Error connecting to server."
          };
          return newMessages;
        }
        return [
          ...prev,
          { role: "assistant", content: "⚠️ Error connecting to server." },
        ];
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] max-w-4xl mx-auto w-full px-4 text-slate-100">
      
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto space-y-6 py-6 pr-2">
        {messages.length === 0 ? (
          /* Empty State / Welcome Screen */
          <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-xl border border-blue-500/30">
              📊
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-white">SEC Filing Financial Agent</h2>
              <p className="text-slate-400 text-sm mt-1">
                Ask anything about ingested 10-Ks, balance sheets, or risk factors.
              </p>
            </div>

            {/* Starter Prompt Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-xl w-full text-left pt-4">
              {[
                "What was ADP's total revenue in fiscal 2021?",
                "List the top privacy risk factors mentioned in Item 1A.",
                "How much cash was returned via share repurchases?",
                "What are ADP's three core strategic pillars?",
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(suggestion)}
                  className="p-3.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-slate-600 rounded-xl text-xs text-slate-300 transition-all text-left group"
                >
                  <p className="group-hover:text-blue-400 font-medium transition-colors">
                    {suggestion}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message List */
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex space-x-3 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-lg bg-blue-600/30 border border-blue-500/40 text-blue-400 flex items-center justify-center font-bold text-xs shrink-0 mt-1">
                  AI
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-slate-800/80 border border-slate-700/60 text-slate-200 rounded-bl-none"
                }`}
              >
                {/* 🛑 2. If assistant message is empty, render loading dots INSIDE the bubble */}
                {msg.role === "assistant" && !msg.content ? (
                  <div className="flex space-x-1.5 items-center py-1">
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                  </div>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))
        )}

        {/* 🛑 3. Removed separate {isLoading && (...)} block to prevent duplicate indicator */}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Modern Prompt Bar */}
      <div className="py-4 bg-slate-950">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative flex items-center bg-slate-800/80 border border-slate-700/80 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 rounded-2xl p-2 transition-all shadow-lg"
        >
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question about the SEC filings..."
            className="w-full bg-transparent text-slate-100 placeholder-slate-400 text-sm px-3 py-1 focus:outline-none resize-none max-h-32"
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white rounded-xl transition-colors shrink-0 ml-2"
          >
            <svg
              className="w-4 h-4 transform rotate-90"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19V5m0 0l-7 7m7-7l7 7"
              />
            </svg>
          </button>
        </form>
        <p className="text-[10px] text-center text-slate-500 mt-2">
          FinRAG can make mistakes. Verify critical financial details against source 10-Ks.
        </p>
      </div>
    </div>
  );
}