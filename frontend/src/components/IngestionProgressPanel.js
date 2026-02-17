import React, { useState, useEffect, useMemo } from 'react';
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
        setStartTime(Date.now());
        let cancelled = false;

        const pollProgress = async () => {
            try {
                const response = await axios.get(`${apiBase}/api/ingest_progress?game=${game}`);
                if (cancelled || !response?.data) return;

                setProgress((prev) => {
                    if (
                        prev &&
                        prev.status === response.data.status &&
                        prev.rows_fetched === response.data.rows_fetched &&
                        prev.total_rows === response.data.total_rows &&
                        prev.progress === response.data.progress &&
                        prev.error === response.data.error
                    ) {
                        return prev;
                    }
                    return response.data;
                });
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

        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [isActive, game, apiBase, onComplete]);

    if (!isActive || !progress) {
        return null;
    }

<<<<<<< HEAD
    const rowsFetched = progress.rows_fetched || 0;
    const totalRows = progress.total_rows || 1;
    const status = progress.status === 'completed' ? 'completed' 
                 : progress.status === 'error' ? 'error' 
                 : 'active';
    const panelStatusClass = status === 'error' ? 'is-error' : status === 'completed' ? 'is-complete' : 'is-active';
=======
    const { rowsFetched, totalRows, status } = useMemo(() => {
        const fetched = Number(progress.rows_fetched || 0);
        const total = Number(progress.total_rows || 1);
        const computedStatus = progress.status === 'completed'
            ? 'completed'
            : progress.status === 'error'
                ? 'error'
                : 'active';

        return { rowsFetched: fetched, totalRows: total, status: computedStatus };
    }, [progress]);
>>>>>>> 165dff8cc451c862093412a10d4f2db017f0a8f6

    return (
        <div className={`ingestion-progress-panel mt-3 ${panelStatusClass}`}>
            <h6 className="ingestion-progress-title">
                🎰 {game.toUpperCase()} Ingestion
            </h6>

            {error && (
                <div className="alert alert-danger ingestion-progress-alert">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {progress.error && (
                <div className="alert alert-danger ingestion-progress-alert">
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
