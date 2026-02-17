import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import './ChatPanelRAG.css';
import getApiBase from '../utils/apiBase';

const API_BASE = getApiBase();

const API_ENDPOINTS = [
    { label: 'Startup Status', method: 'GET', path: '/api/startup_status', description: 'Get startup progress and per-game statuses.', sampleBody: '' },
    { label: 'Start Initialization', method: 'POST', path: '/api/startup_init', description: 'Start background initialization.', sampleBody: '{}' },
    { label: 'List Games', method: 'GET', path: '/api/games', description: 'Get configured lottery games.', sampleBody: '' },
    { label: 'Game Summary', method: 'GET', path: '/api/games/{game}/summary', description: 'Get draw count for a game.', sampleBody: '' },
    { label: 'Manual Ingest', method: 'POST', path: '/api/ingest', description: 'Ingest data for a game.', sampleBody: '{\n  "game": "pick3",\n  "force": false\n}' },
    { label: 'Ingest Progress', method: 'GET', path: '/api/ingest_progress?game={game}', description: 'Get current ingest progress for a game.', sampleBody: '' },
    { label: 'Train Model', method: 'POST', path: '/api/train', description: 'Train model for a game.', sampleBody: '{\n  "game": "pick3"\n}' },
    { label: 'List Experiments', method: 'GET', path: '/api/experiments', description: 'List saved training/prediction experiments.', sampleBody: '' },
    { label: 'Predict Next Draw', method: 'POST', path: '/api/predict', description: 'Run prediction for a game.', sampleBody: '{\n  "game": "pick3",\n  "recent_k": 10\n}' },
    { label: 'Chroma Status', method: 'GET', path: '/api/chroma/status', description: 'Get ChromaDB health/status.', sampleBody: '' },
    { label: 'Health Check', method: 'GET', path: '/health', description: 'Backend health endpoint.', sampleBody: '' },
];

const NEXT_SCHEDULED_DRAW_BY_GAME = {
    take5: 'Daily at 10:30 PM ET',
    pick3: 'Twice daily at ~2:30 PM ET and 10:30 PM ET',
    powerball: 'Mon/Wed/Sat at 10:59 PM ET',
    megamillions: 'Tue/Fri at 11:00 PM ET',
    pick10: 'Daily at 10:30 PM ET',
    cash4life: 'Daily at 9:00 PM ET',
    quickdraw: 'Every 4 minutes (daily schedule)',
    nylotto: 'Wed/Sat at 8:15 PM ET',
};

const GAME_DISPLAY_NAMES = {
    take5: 'Take 5',
    pick3: 'Pick 3',
    powerball: 'Powerball',
    megamillions: 'Mega Millions',
    pick10: 'Pick 10',
    cash4life: 'Cash4Life',
    quickdraw: 'Quick Draw',
    nylotto: 'NY Lotto',
};

function buildInitialConciergeGreeting(selectedGame) {
    const orderedGameKeys = Object.keys(NEXT_SCHEDULED_DRAW_BY_GAME);
    const normalizedSelected = (selectedGame || '').toLowerCase();
    const gameKeys = normalizedSelected && NEXT_SCHEDULED_DRAW_BY_GAME[normalizedSelected]
        ? [normalizedSelected, ...orderedGameKeys.filter((g) => g !== normalizedSelected)]
        : orderedGameKeys;

    const drawLines = gameKeys
        .map((key) => `- **${GAME_DISPLAY_NAMES[key] || key}**: ${NEXT_SCHEDULED_DRAW_BY_GAME[key]}`)
        .join('\n');

    return (
        'Hi! I am your Mensa Concierge — friendly, helpful, and expert in Python, React, and ChromaDB RAG. '\n+
        + 'I can chat, manage files, run internet search, and perform self diagnostics.\n\n'
        + '**Next scheduled draw per game (ET):**\n'
        + `${drawLines}\n\n`
        + '_Schedules can change; confirm official times on NY Lottery._'
    );
}

function renderMarkdown(text) {
    if (typeof text !== 'string') {
        return '';
    }
    const rawMarkup = marked(text);
    return rawMarkup;
}

const ChatPanel = ({ game = null }) => {
    const [messages, setMessages] = useState(() => ([
        {
            sender: 'bot',
            text: buildInitialConciergeGreeting(game),
            sources: []
        }
    ]));
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [useRag, setUseRag] = useState(true);
    const [toolPath, setToolPath] = useState('.');
    const [toolReadPath, setToolReadPath] = useState('README.md');
    const [toolWritePath, setToolWritePath] = useState('message_from_agent.txt');
    const [toolWriteContent, setToolWriteContent] = useState('Hello from Mensa Concierge.');
    const [toolSearchQuery, setToolSearchQuery] = useState('latest ChromaDB retrieval best practices');
    const [selectedApiEndpoint, setSelectedApiEndpoint] = useState(API_ENDPOINTS[0].label);
    const [apiMethod, setApiMethod] = useState(API_ENDPOINTS[0].method);
    const [apiPath, setApiPath] = useState(API_ENDPOINTS[0].path);
    const [apiBody, setApiBody] = useState(API_ENDPOINTS[0].sampleBody);
    const [apiGame, setApiGame] = useState(game || 'pick3');
    const [apiDescription, setApiDescription] = useState(API_ENDPOINTS[0].description);
    const [latestApiIO, setLatestApiIO] = useState(null);
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

    useEffect(() => {
        const endpoint = API_ENDPOINTS.find((item) => item.label === selectedApiEndpoint);
        if (!endpoint) return;
        setApiMethod(endpoint.method);
        setApiPath(endpoint.path);
        setApiBody(endpoint.sampleBody || '');
        setApiDescription(endpoint.description || '');
    }, [selectedApiEndpoint]);

    useEffect(() => {
        if (game) {
            setApiGame(game);
        }
    }, [game]);

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

    const runApiEndpoint = async () => {
        const resolvedGame = (apiGame || game || 'pick3').toLowerCase();
        const resolvedPath = (apiPath || '')
            .replaceAll('{game}', encodeURIComponent(resolvedGame));

        if (!resolvedPath.startsWith('/')) {
            setLatestApiIO({
                request: { method: apiMethod, path: resolvedPath, body: apiBody || null },
                response: { error: 'API path must start with /' },
                ok: false,
                status: 0,
            });
            return;
        }

        const requestBody = (apiBody || '').trim();
        let parsedBody = null;

        if (apiMethod !== 'GET' && requestBody) {
            try {
                parsedBody = JSON.parse(requestBody);
            } catch (error) {
                setLatestApiIO({
                    request: { method: apiMethod, path: resolvedPath, body: requestBody },
                    response: { error: `Invalid JSON body: ${error.message}` },
                    ok: false,
                    status: 0,
                });
                return;
            }
        }

        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE}${resolvedPath}`, {
                method: apiMethod,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: apiMethod === 'GET' ? undefined : JSON.stringify(parsedBody || {}),
            });

            let data;
            try {
                data = await response.json();
            } catch {
                data = { message: 'Response was not valid JSON.' };
            }

            setLatestApiIO({
                request: { method: apiMethod, path: resolvedPath, body: parsedBody },
                response: data,
                ok: response.ok,
                status: response.status,
            });

            setMessages((prev) => [
                ...prev,
                {
                    sender: 'bot',
                    text: `API ${apiMethod} ${resolvedPath} returned status ${response.status}.`,
                    sources: [],
                },
            ]);
        } catch (error) {
            setLatestApiIO({
                request: { method: apiMethod, path: resolvedPath, body: parsedBody },
                response: { error: error.message || 'API request failed.' },
                ok: false,
                status: 0,
            });
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

            <div className="chat-workspace">
                <div className="chat-left-column">
                    <div className="px-3 pt-2 pb-2 border-bottom chat-utility-strip">
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
                            Left column: controls and support inputs. Right column: chat output and API input/output.
                        </div>
                    </div>

                    <div className="chat-input-form-rag chat-tool-form">
                        <div className="small fw-semibold mb-2">API Endpoint Runner</div>
                        <div className="row g-2">
                            <div className="col-12">
                                <label className="form-label small">Endpoint</label>
                                <select className="form-select form-select-sm" value={selectedApiEndpoint} onChange={(e) => setSelectedApiEndpoint(e.target.value)} disabled={isLoading}>
                                    {API_ENDPOINTS.map((item) => (
                                        <option key={item.label} value={item.label}>{item.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="col-4">
                                <label className="form-label small">Method</label>
                                <input className="form-control form-control-sm" value={apiMethod} onChange={(e) => setApiMethod(e.target.value.toUpperCase())} disabled={isLoading} />
                            </div>
                            <div className="col-8">
                                <label className="form-label small">Path</label>
                                <input className="form-control form-control-sm" value={apiPath} onChange={(e) => setApiPath(e.target.value)} disabled={isLoading} />
                            </div>
                            <div className="col-12">
                                <label className="form-label small">Game Placeholder Value</label>
                                <input className="form-control form-control-sm" value={apiGame} onChange={(e) => setApiGame(e.target.value)} disabled={isLoading} />
                            </div>
                            <div className="col-12">
                                <label className="form-label small">Description</label>
                                <div className="small text-muted api-description-text">{apiDescription}</div>
                            </div>
                            <div className="col-12">
                                <label className="form-label small">JSON Body (for non-GET)</label>
                                <textarea className="form-control form-control-sm" rows={4} value={apiBody} onChange={(e) => setApiBody(e.target.value)} disabled={isLoading} />
                            </div>
                            <div className="col-12 d-flex justify-content-end">
                                <button className="btn btn-sm btn-outline-primary" type="button" disabled={isLoading} onClick={runApiEndpoint}>Run Endpoint</button>
                            </div>
                        </div>
                    </div>

                    <div className="chat-input-form-rag chat-tool-form">
                        <div className="small fw-semibold mb-2">Support Tools</div>
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
                </div>

                <div className="chat-right-column">
                    <div className="chat-io-panel border-bottom px-3 py-2">
                        <div className="small fw-semibold mb-2">Right Column API I/O</div>
                        {!latestApiIO ? (
                            <div className="small text-muted">Run an endpoint from the left panel to see request input and response output here.</div>
                        ) : (
                            <div className="row g-2">
                                <div className="col-12 col-lg-6">
                                    <div className="small fw-semibold mb-1">Input</div>
                                    <pre className="tool-result-pre mb-0"><code>{JSON.stringify(latestApiIO.request, null, 2)}</code></pre>
                                </div>
                                <div className="col-12 col-lg-6">
                                    <div className="small fw-semibold mb-1">Output</div>
                                    <div className={`small mb-1 ${latestApiIO.ok ? 'text-success' : 'text-danger'}`}>
                                        Status: {latestApiIO.status}
                                    </div>
                                    <pre className="tool-result-pre mb-0"><code>{JSON.stringify(latestApiIO.response, null, 2)}</code></pre>
                                </div>
                            </div>
                        )}
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
                                    {msg.sender === 'bot' && msg.contextUsed && msg.sources && msg.sources.length > 0 && (
                                        <div className="sources-badge">
                                            📚 {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                                        </div>
                                    )}
                                </div>

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
                                            <details className="tool-result-details">
                                                <summary>View tool output</summary>
                                                <pre className="tool-result-pre">
                                                    <code>{JSON.stringify(msg.toolResult, null, 2)}</code>
                                                </pre>
                                            </details>
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

                    <form onSubmit={handleSendMessage} className="chat-input-form-rag">
                        <p className="chat-input-title">Chat Input</p>
                        <div className="input-wrapper">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder={useRag ? "Ask me about lottery data, workflow errors, or code fixes..." : "Ask anything — I’ll help step by step..."}
                                disabled={isLoading}
                                className="chat-input-rag"
                                aria-label="Chat message input"
                            />
                            <button
                                type="submit"
                                disabled={isLoading || !input.trim()}
                                className="chat-send-btn"
                            >
                                {isLoading ? 'Sending...' : 'Send'}
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
            </div>
        </div>
    );
};

export default ChatPanel;
