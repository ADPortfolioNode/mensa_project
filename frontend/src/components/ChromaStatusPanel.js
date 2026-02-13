import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import chromaStateManager from '../utils/chromaStateManager';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ChromaStatusPanel() {
    const [collections, setCollections] = useState([]);
    const [meta, setMeta] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [apiBase, setApiBase] = useState(null);
    const inFlightRef = useRef(false);

    const fetchCollectionsWithRetry = async (baseUrl, maxAttempts = 3) => {
        let lastError = null;
        for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
            try {
                const response = await axios.get(`${baseUrl}/api/chroma/collections`, { timeout: 12000 });
                return response;
            } catch (err) {
                lastError = err;
                if (attempt < maxAttempts) {
                    await sleep(attempt * 700);
                }
            }
        }
        throw lastError;
    };

    const fetchChromaStatus = async (baseUrl, options = { silent: false }) => {
        const { silent } = options;
        if (baseUrl === null || baseUrl === undefined) {
            setError("API base not configured");
            setLoading(false);
            return;
        }

        if (inFlightRef.current) {
            return;
        }

        inFlightRef.current = true;
        if (silent) {
            setRefreshing(true);
        } else {
            setLoading(true);
        }

        try {
            const response = await fetchCollectionsWithRetry(baseUrl);
            const cols = response.data?.collections || [];
            const responseMeta = response.data?.meta || null;
            setCollections(cols);
            setMeta(responseMeta);
            setError(response.data?.error || null);
        } catch (err) {
            console.error("Failed to fetch ChromaDB collections status:", err);
            const errorMsg = err.response?.status === 404
                ? "ChromaDB not responding. Please check backend connection."
                : err.code === 'ECONNABORTED'
                ? "Request timeout. Backend may still be starting up."
                : "Failed to fetch ChromaDB collections status right now.";
            setError(errorMsg);
        } finally {
            inFlightRef.current = false;
            setLoading(false);
            setRefreshing(false);
        }
    };

    // Initialize API base
    useEffect(() => {
        const base = getApiBase();
        setApiBase(base);
        fetchChromaStatus(base, { silent: false });
    }, []);

    // Refresh only when ingestion/upload updates collections
    useEffect(() => {
        if (apiBase === null || apiBase === undefined) return;
        const unsubscribe = chromaStateManager.subscribe(() => {
            fetchChromaStatus(apiBase, { silent: true });
        });
        return () => unsubscribe();
    }, [apiBase]);

    return (
        <div className="card p-3 mb-3 h-100">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h5 style={{ margin: 0 }}>ChromaDB Collections Status</h5>
                {refreshing && !loading && !error && (
                    <span style={{ fontSize: '12px', color: '#6c757d' }}>Refreshing...</span>
                )}
                {error && (
                    <button 
                        onClick={() => fetchChromaStatus(apiBase, { silent: false })}
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
                    <p>Loading collections...</p>
                </div>
            )}
            {error && collections.length === 0 && (
                <div className="alert alert-danger" style={{ marginBottom: 0 }}>
                    <strong>Error:</strong> {error}
                </div>
            )}
            {error && collections.length > 0 && (
                <div className="alert alert-warning" style={{ marginBottom: '12px' }}>
                    <strong>Warning:</strong> {error} Showing last known collections.
                </div>
            )}
            {!loading && !error && collections.length === 0 && (
                <p style={{ color: '#6c757d' }}>No ChromaDB collections found. Run ingestion to populate.</p>
            )}
            {meta && (
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px' }}>
                    Record index: {meta.record_index_basis || 'configured order'}
                </div>
            )}
            {collections.length > 0 && (
                <ul className="list-group list-group-flush">
                    {collections.map((collection, index) => (
                        <li key={`${collection.name}-${index}`} className="list-group-item d-flex justify-content-between align-items-center">
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span style={{ fontWeight: 'bold' }}>{collection.name.toUpperCase()}</span>
                                <small style={{ color: '#6c757d' }}>Index #{collection.record_index || (index + 1)}</small>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {(collection.state === 'timeout' || collection.state === 'error') && (
                                    <span className="badge bg-warning text-dark rounded-pill">{collection.state}</span>
                                )}
                                <span className="badge bg-info rounded-pill">
                                    {Number(collection.count || 0).toLocaleString()} docs
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
