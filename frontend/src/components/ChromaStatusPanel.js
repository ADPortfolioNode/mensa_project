import React, { useState, useEffect } from 'react';
import axios from 'axios';

function normalizeApiBase(raw) {
    const v = (raw || '').toString().trim().replace(/\/+$/, '');
    if (!v) return '';
    if (!/^https?:\/\//i.test(v)) {
        return `http://${v}`;
    }
    return v;
}

const API_BASE = normalizeApiBase(process.env.REACT_APP_API_BASE);

export default function ChromaStatusPanel() {
    const [collections, setCollections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchChromaStatus = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${API_BASE}/api/chroma/collections`);
            setCollections(response.data);
        } catch (err) {
            console.error("Failed to fetch ChromaDB collections status:", err);
            setError("Failed to fetch ChromaDB collections status.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchChromaStatus();
        const interval = setInterval(fetchChromaStatus, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="card p-3 mb-3 h-100">
            <h5>ChromaDB Collections Status</h5>
            {loading && (
                <div className="text-center">
                    <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </div>
                    <p>Loading collections...</p>
                </div>
            )}
            {error && (
                <div className="alert alert-danger">
                    <strong>Error:</strong> {error}
                </div>
            )}
            {!loading && collections.length === 0 && !error && (
                <p>No ChromaDB collections found.</p>
            )}
            {!loading && collections.length > 0 && (
                <ul className="list-group list-group-flush">
                    {collections.map(collection => (
                        <li key={collection.name} className="list-group-item d-flex justify-content-between align-items-center">
                            {collection.name}
                            <span className="badge bg-info rounded-pill">
                                {collection.count} documents
                            </span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
