import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import './ChatPanelRAG.css';
import getApiBase from '../utils/apiBase';

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
    const [toolPath, setToolPath] = useState('.');
    const [toolReadPath, setToolReadPath] = useState('README.md');
    const [toolWritePath, setToolWritePath] = useState('message_from_agent.txt');
    const [toolWriteContent, setToolWriteContent] = useState('Hello from Mensa Concierge.');
    const [toolSearchQuery, setToolSearchQuery] = useState('latest ChromaDB retrieval best practices');
    const messagesEndRef = useRef(null);

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

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

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

            <div className="px-3 pt-2 pb-1 border-bottom" style={{ background: '#f6f6f6' }}>
                <div className="small fw-semibold mb-2">Quick Actions</div>
                <div className="d-flex flex-wrap gap-2 mb-2">
                    {quickActions.map((action) => (
                        <button
                            key={action.label}
                            type="button"
                            className="btn btn-sm btn-outline-secondary"
                            disabled={isLoading}
                            onClick={action.run}
                        >
                            {action.label}
                        </button>
                    ))}
                </div>
                <div className="small text-muted">
                    I can help with coding, debugging, architecture, file operations, web research, and runtime diagnostics.
                </div>
            </div>

            <div className="chat-window-rag">
                {messages.map((msg, index) => (
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
                        </div>

                        {/* Expandable sources display */}
                        {msg.sources && msg.sources.length > 0 && (
                            <div className="message-sources">
                                {msg.sources.map((source, i) => (
                                    <div key={i} className="source-item">
                                        <span className="source-game">{source.game}</span>
                                        <span className="source-content">{source.content}</span>
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

                {isLoading && (
                    <div className="chat-message-rag bot">
                        <div className="message-bubble loading">
                            <span className="spinner-dot"></span>
                            <span className="spinner-dot"></span>
                            <span className="spinner-dot"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-form-rag" style={{ borderTop: '1px solid #d9d9d9', background: '#fafafa' }}>
                <div className="row g-2">
                    <div className="col-md-6">
                        <label className="form-label small">Browse Path</label>
                        <input className="form-control form-control-sm" value={toolPath} onChange={(e) => setToolPath(e.target.value)} disabled={isLoading} />
                    </div>
                    <div className="col-md-6 d-flex align-items-end gap-2">
                        <button className="btn btn-sm btn-outline-primary" type="button" disabled={isLoading} onClick={() => callTool('list_files', { path: toolPath })}>List Files</button>
                        <button className="btn btn-sm btn-outline-dark" type="button" disabled={isLoading} onClick={() => callTool('self_diagnostics', {})}>Self Diagnostics</button>
                    </div>
                    <div className="col-md-6">
                        <label className="form-label small">Read File</label>
                        <input className="form-control form-control-sm" value={toolReadPath} onChange={(e) => setToolReadPath(e.target.value)} disabled={isLoading} />
                    </div>
                    <div className="col-md-6 d-flex align-items-end">
                        <button className="btn btn-sm btn-outline-success" type="button" disabled={isLoading} onClick={() => callTool('read_file', { path: toolReadPath, start_line: 1, end_line: 200 })}>Read File</button>
                    </div>
                    <div className="col-md-6">
                        <label className="form-label small">Write File Path</label>
                        <input className="form-control form-control-sm" value={toolWritePath} onChange={(e) => setToolWritePath(e.target.value)} disabled={isLoading} />
                    </div>
                    <div className="col-md-6">
                        <label className="form-label small">Internet Search</label>
                        <div className="d-flex gap-2">
                            <input className="form-control form-control-sm" value={toolSearchQuery} onChange={(e) => setToolSearchQuery(e.target.value)} disabled={isLoading} />
                            <button className="btn btn-sm btn-outline-info" type="button" disabled={isLoading} onClick={() => callTool('internet_search', { query: toolSearchQuery })}>Search</button>
                        </div>
                    </div>
                    <div className="col-12">
                        <label className="form-label small">Write Content</label>
                        <textarea className="form-control form-control-sm" rows={2} value={toolWriteContent} onChange={(e) => setToolWriteContent(e.target.value)} disabled={isLoading} />
                    </div>
                    <div className="col-12 d-flex justify-content-end">
                        <button className="btn btn-sm btn-outline-warning" type="button" disabled={isLoading} onClick={() => callTool('write_file', { path: toolWritePath, content: toolWriteContent, mode: 'overwrite' })}>Write File</button>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-form-rag">
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
        </div>
    );
};

export default ChatPanel;
