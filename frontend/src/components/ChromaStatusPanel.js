import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';

export default function ChromaStatusPanel() {
    const [status, setStatus] = useState('unknown');
    const [collections, setCollections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [apiBase, setApiBase] = useState(null);

    const fetchChromaStatus = useCallback(async (baseUrl) => {
        if (!baseUrl) {
            setError("API base not configured");
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${baseUrl}/api/chroma/collections`, { timeout: 5000 });
            const nextStatus = response.data?.status || 'unknown';
            const nextCollections = response.data?.collections || [];
            setStatus(nextStatus);
            setCollections(nextCollections);
            if (nextStatus === 'error' && response.data?.error) {
                setError(response.data.error);
            }
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch ChromaDB collections status:", err);
            const errorMsg = err.response?.status === 404
                ? "ChromaDB not responding. Please check backend connection."
                : err.code === 'ECONNABORTED'
                ? "Request timeout. Backend may be starting up."
                : "Failed to fetch ChromaDB collections status.";
            setError(errorMsg);
            setCollections([]);
            setLoading(false);
        }
    }, []);

    // Initialize API base
    useEffect(() => {
        const base = getApiBase();
        setApiBase(base);
        if (base) {
            fetchChromaStatus(base);
        }
    }, []);
    
    // Set up polling interval
    useEffect(() => {
        if (!apiBase) return;
        const interval = setInterval(() => fetchChromaStatus(apiBase), 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, [apiBase, fetchChromaStatus]);

    useEffect(() => {
        if (!apiBase) return;

        const handleRefresh = () => {
            fetchChromaStatus(apiBase);
        };

        window.addEventListener('chroma:refresh', handleRefresh);
        return () => window.removeEventListener('chroma:refresh', handleRefresh);
    }, [apiBase, fetchChromaStatus]);

    return (
        <div className="card p-3 mb-3 h-100">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h5 style={{ margin: 0 }}>ChromaDB Collections</h5>
                {error && (
                    <button 
                        onClick={() => fetchChromaStatus(apiBase)}
                        style={{
                            padding: '4px 8px',
                            fontSize: '12px',
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '3px',
                            cursor: 'pointer'
                        }}
                    >
                        Retry
                    </button>
                )}
            </div>
            {loading && (
                <div className="text-center">
                    <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p>Loading status...</p>
                </div>
            )}
            {error && (
                <div className="alert alert-danger" style={{ marginBottom: 0 }}>
                    <strong>Error:</strong> {error}
                </div>
            )}
            {!loading && !error && (
                <div>
                    <div style={{
                        height: '16px',
                        background: '#1c1f24',
                        borderRadius: '999px',
                        border: '1px solid rgba(255,255,255,0.1)',
                        overflow: 'hidden',
                        marginBottom: '10px'
                    }}>
                        <div style={{
                            height: '100%',
                            width: status === 'ok' ? '100%' : status === 'unknown' ? '40%' : '15%',
                            background: status === 'ok' ? '#00ff88' : status === 'unknown' ? '#ffc107' : '#ff5c5c',
                            transition: 'width 0.4s ease'
                        }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span>Live status</span>
                        <strong>{status.toUpperCase()}</strong>
                    </div>
                    <div style={{ marginTop: '12px' }}>
                        {collections.length === 0 ? (
                            <div style={{ fontSize: '12px', color: '#9aa3ad' }}>
                                No collections found yet.
                            </div>
                        ) : (
                            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                                        <th style={{ padding: '6px 0' }}>Collection</th>
                                        <th style={{ padding: '6px 0', textAlign: 'right' }}>Count</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {collections.map((item) => (
                                        <tr key={item.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                            <td style={{ padding: '6px 0' }}>{item.name}</td>
                                            <td style={{ padding: '6px 0', textAlign: 'right' }}>
                                                {item.count ?? 0}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
