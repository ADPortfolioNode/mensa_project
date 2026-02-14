import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import './ChatPanelRAG.css';
import getApiBase from '../utils/apiBase';
import { hasBonusSignal, highlightBonusTermsAsSafeHtml } from '../utils/chatBonusUtils';

const API_BASE = getApiBase();

function renderMarkdown(text) {
    if (typeof text !== 'string') {
        return '';
    }
    const rawMarkup = marked(text);
    return rawMarkup;
}

const ChatPanel = ({ game = null }) => {
    const [messages, setMessages] = useState([
        { 
            sender: 'bot', 
            text: 'Hi! I am your Mensa Concierge — friendly, helpful, and expert in Python, React, and ChromaDB RAG. I can chat, manage files, run internet search, and perform self diagnostics.',
            sources: []
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [useRag, setUseRag] = useState(true);
    const chatWindowRef = useRef(null);

    const quickActions = [
        {
            label: 'Diagnose now',
            run: () => callTool('self_diagnostics', {}),
        },
        {
            label: 'Read README',
            run: () => callTool('read_file', { path: 'README.md', start_line: 1, end_line: 220 }),
        },
        {
            label: 'List backend/services',
            run: () => callTool('list_files', { path: 'backend/services' }),
        },
        {
            label: 'Search ChromaDB RAG',
            run: () => callTool('internet_search', { query: 'ChromaDB RAG best practices 2026' }),
        },
    ];

    useEffect(() => {
        Prism.highlightAll();
    }, [messages]);

    const scrollToTop = () => {
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    useEffect(() => {
        scrollToTop();
    }, [messages]);

    const orderedMessages = [...messages].reverse();

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = { sender: 'user', text: input };
        setMessages((prevMessages) => [...prevMessages, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const payload = {
                text: input,
                game: game,
                use_rag: useRag
            };

            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            const botMessageText = data.response || "Sorry, I didn't understand that.";
            const botMessage = { 
                sender: 'bot', 
                text: botMessageText,
                sources: data.sources || [],
                contextUsed: data.context_used || false,
                sourcesCount: data.sources_count || 0,
                toolName: data.tool_name || null,
                toolResult: data.tool_result || null
            };

            setMessages((prevMessages) => [...prevMessages, botMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = { 
                sender: 'bot', 
                text: 'Error: Could not connect to the server. Please try again.',
                sources: []
            };
            setMessages((prevMessages) => [...prevMessages, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleRag = () => {
        setUseRag(!useRag);
    };

    const callTool = async (name, params) => {
        const helperText = `Running tool: ${name}`;
        setMessages((prev) => [...prev, { sender: 'user', text: helperText }]);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: helperText,
                    game,
                    use_rag: false,
                    tool: {
                        name,
                        params,
                    },
                }),
            });

            const data = await response.json();
            const botMessage = {
                sender: 'bot',
                text: data.response || 'Tool execution finished.',
                sources: [],
                contextUsed: false,
                toolName: data.tool_name || name,
                toolResult: data.tool_result || null,
            };
            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            setMessages((prev) => [
                ...prev,
                {
                    sender: 'bot',
                    text: `Error running tool '${name}': ${error.message}`,
                    sources: [],
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-panel-rag">
            <div className="chat-header-rag">
                <div className="chat-header-left">
                    <h3>Mensa Concierge</h3>
                    {game && <span className="chat-game-badge">{game.toUpperCase()}</span>}
                </div>
                <div className="chat-header-right">
                    <label className="rag-toggle">
                        <input 
                            type="checkbox" 
                            checked={useRag} 
                            onChange={toggleRag}
                            disabled={isLoading}
                        />
                        <span className={`toggle-label ${useRag ? 'active' : ''}`}>
                            RAG {useRag ? 'ON' : 'OFF'}
                        </span>
                    </label>
                </div>
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-form-rag">
                <div className="quick-actions-rag">
                    <div className="quick-actions-title">Quick Actions</div>
                    <div className="quick-actions-buttons">
                        {quickActions.map((action) => (
                            <button
                                key={action.label}
                                type="button"
                                className="quick-action-btn"
                                disabled={isLoading}
                                onClick={action.run}
                            >
                                {action.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="input-wrapper">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={useRag ? "Ask me about lottery data, workflow errors, or code fixes..." : "Ask anything — I’ll help step by step..."}
                        disabled={isLoading}
                        className="chat-input-rag"
                    />
                    <button 
                        type="submit" 
                        disabled={isLoading || !input.trim()}
                        className="chat-send-btn"
                    >
                        {isLoading ? '...' : '→'}
                    </button>
                </div>
                {useRag && (
                    <div className="rag-info">
                        <span className="info-icon">ℹ️</span>
                        <span>RAG enabled: I ground answers using ChromaDB context before responding.</span>
                    </div>
                )}
            </form>

            <div className="chat-window-rag" ref={chatWindowRef}>
                {isLoading && (
                    <div className="chat-message-rag bot">
                        <div className="message-bubble loading">
                            <span className="spinner-dot"></span>
                            <span className="spinner-dot"></span>
                            <span className="spinner-dot"></span>
                        </div>
                    </div>
                )}

                {orderedMessages.map((msg, index) => (
                    <div key={index} className={`chat-message-rag ${msg.sender}`}>
                        <div className="message-container">
                            <div className="message-bubble">
                                {msg.sender === 'user' ? (
                                    msg.text
                                ) : (
                                    <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }} />
                                )}
                            </div>
                            
                            {/* Show sources badge if RAG was used */}
                            {msg.sender === 'bot' && msg.contextUsed && msg.sources && msg.sources.length > 0 && (
                                <div className="sources-badge">
                                    📚 {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                                </div>
                            )}

                            {hasBonusSignal(msg) && (
                                <div className="bonus-badge" role="status" aria-label="Bonus number indicated in this response">
                                    🎯 Bonus number included
                                </div>
                            )}
                        </div>

                        {/* Expandable sources display */}
                        {msg.sources && msg.sources.length > 0 && (
                            <div className="message-sources">
                                {msg.sources.map((source, i) => (
                                    <div key={i} className="source-item">
                                        <span className="source-game">{source.game}</span>
                                        <span className="source-content" dangerouslySetInnerHTML={{ __html: highlightBonusTermsAsSafeHtml(source.content) }} />
                                        <span className="source-distance">Score: {(1 - source.distance).toFixed(3)}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        {msg.toolResult && (
                            <div className="message-sources">
                                <div className="source-item">
                                    <span className="source-game">Tool: {msg.toolName || 'tool'}</span>
                                    <span className="source-content">{JSON.stringify(msg.toolResult, null, 2)}</span>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ChatPanel;
