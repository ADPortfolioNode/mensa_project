import React, { useState, useEffect } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import ProgressiveProgressBar from './ProgressiveProgressBar';

/**
 * IngestionProgressPanel
 * Shows real-time progress during manual ingestion
 * Polls the /api/ingest_progress endpoint
 */
export default function IngestionProgressPanel({ game, isActive, onComplete }) {
    const [progress, setProgress] = useState(null);
    const [error, setError] = useState(null);
    const [startTime, setStartTime] = useState(null);
    const apiBase = getApiBase();

    useEffect(() => {
        if (!isActive || !game || apiBase === null || apiBase === undefined) {
            setProgress(null);
            setStartTime(null);
            return;
        }

        // Set start time when ingestion begins
        if (!startTime) {
            setStartTime(Date.now());
        }

        const pollProgress = async () => {
            try {
                const response = await axios.get(`${apiBase}/api/ingest_progress?game=${game}`);
                setProgress(response.data);
                setError(null);

                // Call onComplete if ingestion finished
                if (response.data.status === 'completed' || response.data.status === 'error') {
                    onComplete?.(response.data);
                }
            } catch (err) {
                console.error("Failed to fetch ingestion progress:", err);
                setError("Failed to fetch progress");
            }
        };

        // Poll immediately and then every 500ms
        pollProgress();
        const interval = setInterval(pollProgress, 500);

        return () => clearInterval(interval);
    }, [isActive, game, apiBase, onComplete, startTime]);

    if (!isActive || !progress) {
        return null;
    }

    const rowsFetched = progress.rows_fetched || 0;
    const totalRows = progress.total_rows || 1;
    const status = progress.status === 'completed' ? 'completed' 
                 : progress.status === 'error' ? 'error' 
                 : 'active';

    return (
        <div style={{
            padding: '16px',
            backgroundColor: status === 'error' ? '#f8d7da' : status === 'completed' ? '#d4edda' : '#fff3cd',
            border: `2px solid ${status === 'error' ? '#f5c6cb' : status === 'completed' ? '#c3e6cb' : '#ffeaa7'}`,
            borderRadius: '8px',
            marginTop: '16px'
        }}>
            <h6 style={{ marginBottom: '12px', fontWeight: 'bold' }}>
                🎰 {game.toUpperCase()} Ingestion
            </h6>

            {error && (
                <div className="alert alert-danger" style={{ marginBottom: '12px', padding: '8px' }}>
                    <strong>Error:</strong> {error}
                </div>
            )}

            {progress.error && (
                <div className="alert alert-danger" style={{ marginBottom: '12px', padding: '8px' }}>
                    <strong>Ingestion Failed:</strong> {progress.error}
                </div>
            )}

            {!progress.error && (
                <ProgressiveProgressBar
                    current={rowsFetched}
                    total={totalRows}
                    status={status}
                    label={`Fetching ${game} data`}
                    showMetadata={true}
                    startTime={startTime}
                    colorScheme="primary"
                />
            )}
        </div>
    );
}
