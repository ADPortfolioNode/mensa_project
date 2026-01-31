import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import './ChatPanel.css';

const API_BASE = process.env.REACT_APP_API_BASE || '';

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
            text: 'Hello! I am your AI assistant powered by RAG (Retrieval-Augmented Generation). I can answer questions about lottery games using real data from our database.',
            sources: []
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [useRag, setUseRag] = useState(true);
    const [showSources, setShowSources] = useState(false);
    const [lastSources, setLastSources] = useState([]);
    const messagesEndRef = useRef(null);

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
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    text: input,
                    game: game,
                    use_rag: useRag
                }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = response.json();
            
            const botMessageText = data.response || "Sorry, I didn't understand that.";
            const botMessage = { 
                sender: 'bot', 
                text: botMessageText,
                sources: data.sources || [],
                contextUsed: data.context_used || false,
                sourcesCount: data.sources_count || 0
            };

            setMessages((prevMessages) => [...prevMessages, botMessage]);
            
            // Store sources for display
            if (data.sources && data.sources.length > 0) {
                setLastSources(data.sources);
            }
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

    return (
        <div className="chat-panel-rag">
            <div className="chat-header-rag">
                <div className="chat-header-left">
                    <h3>AI Chat Assistant</h3>
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

            <form onSubmit={handleSendMessage} className="chat-input-form-rag">
                <div className="input-wrapper">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={useRag ? "Ask about lottery data (using database context)..." : "Ask anything..."}
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
                        <span>RAG enabled: Responses use database context for accuracy</span>
                    </div>
                )}
            </form>
        </div>
    );
};

export default ChatPanel;
