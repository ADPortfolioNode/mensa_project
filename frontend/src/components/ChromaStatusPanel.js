import React, { useState, useEffect } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';

export default function ChromaStatusPanel() {
    const [collections, setCollections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [apiBase, setApiBase] = useState(null);

    const fetchChromaStatus = async (baseUrl) => {
        if (!baseUrl) {
            setError("API base not configured");
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${baseUrl}/api/chroma/collections`, { timeout: 5000 });
            // Backend returns {status, collections} - extract collections array
            const cols = response.data.collections || [];
            setCollections(cols);
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch ChromaDB collections status:", err);
            const errorMsg = err.response?.status === 404
                ? "ChromaDB not responding. Please check backend connection."
                : err.code === 'ECONNABORTED'
                ? "Request timeout. Backend may be starting up."
                : "Failed to fetch ChromaDB collections status.";
            setError(errorMsg);
            setLoading(false);
        }
    };

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
    }, [apiBase]);

    return (
        <div className="card p-3 mb-3 h-100">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h5 style={{ margin: 0 }}>ChromaDB Collections Status</h5>
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
                    <p>Loading collections...</p>
                </div>
            )}
            {error && (
                <div className="alert alert-danger" style={{ marginBottom: 0 }}>
                    <strong>Error:</strong> {error}
                </div>
            )}
            {!loading && !error && collections.length === 0 && (
                <p style={{ color: '#6c757d' }}>No ChromaDB collections found. Run ingestion to populate.</p>
            )}
            {!loading && !error && collections.length > 0 && (
                <ul className="list-group list-group-flush">
                    {collections.map((collection, index) => (
                        <li key={`${collection.name}-${index}`} className="list-group-item d-flex justify-content-between align-items-center">
                            <span style={{ fontWeight: 'bold' }}>{collection.name.toUpperCase()}</span>
                            <span className="badge bg-info rounded-pill">
                                {collection.count} docs
                            </span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
