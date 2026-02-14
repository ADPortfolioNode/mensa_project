import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import './ChatPanel.css';
import getApiBase from '../utils/apiBase';
import { hasBonusSignal, highlightBonusTermsInHtml } from '../utils/chatBonusUtils';

const API_BASE = getApiBase();

function renderMarkdown(text) {
    if (typeof text !== 'string') {
        return '';
    }
    const rawMarkup = marked(text);
    return highlightBonusTermsInHtml(rawMarkup);
}

const ChatPanel = () => {
    const [messages, setMessages] = useState([
        { sender: 'bot', text: 'Hello! I am a helpful assistant. You can ask me about the lottery games, the model, or the predictions.' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
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
                body: JSON.stringify({ text: input }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            const botMessageText = data.response?.response || "Sorry, I didn't understand that.";
            const botMessage = { sender: 'bot', text: botMessageText };

            setMessages((prevMessages) => [...prevMessages, botMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = { sender: 'bot', text: 'Error: Could not connect to the server.' };
            setMessages((prevMessages) => [...prevMessages, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-panel">
            <div className="chat-window">
                {messages.map((msg, index) => (
                    <div key={index} className={`chat-message ${msg.sender}`}>
                        {msg.sender === 'user' ? (
                            <div className="message-bubble">{msg.text}</div>
                        ) : (
                            <>
                                <div className="message-bubble" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }} />
                                {hasBonusSignal(msg) && (
                                    <div className="bonus-badge" role="status" aria-label="Bonus number indicated in this response">
                                        🎯 Bonus number included
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                ))}
                {isLoading && (
                    <div className="chat-message bot">
                        <div className="message-bubble">Thinking...</div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <form onSubmit={handleSendMessage} className="chat-input-form">
                <div className="chat-input-shell">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask the agent anything..."
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={isLoading}>Send</button>
                </div>
            </form>
        </div>
    );
};

export default ChatPanel;
