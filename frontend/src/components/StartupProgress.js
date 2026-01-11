import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { analyzeError, ErrorCategory } from '../utils/errorUtils';
import ErrorMessage from './ErrorMessage';

const StartupProgress = ({ onComplete }) => {
    const [status, setStatus] = useState(null);
    const [errorReport, setErrorReport] = useState(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await axios.get('http://localhost:5000/api/startup_status');
                setErrorReport(null); // Clear previous errors on a successful connection
                setStatus(response.data);
                if (response.data.status === 'completed') {
                    onComplete();
                }
            } catch (error) {
                console.error("Error fetching startup status:", error);
                const report = analyzeError(error);
                setErrorReport(report);
                // If it's a connection error, stop polling
                if (report.category === ErrorCategory.CONNECTION_ERROR) {
                    clearInterval(interval);
                }
            }
        };

        const interval = setInterval(fetchStatus, 2000); // Poll every 2 seconds
        fetchStatus(); // Initial fetch

        return () => clearInterval(interval);
    }, [onComplete]);

    if (errorReport) {
        return (
            <div style={{ padding: '20px' }}>
                <ErrorMessage errorReport={errorReport} />
            </div>
        );
    }

    if (!status || status.status === 'pending') {
        return <div>Initializing...</div>;
    }

    const overallProgress = status.total > 0 ? (status.progress / status.total) * 100 : 100;

    return (
        <div style={{ padding: '20px' }}>
            <h2>Lottery App Initializing...</h2>
            <p>Status: {status.status}</p>
            {status.current_task && <p>{status.current_task}</p>}

            <h4>Overall Progress:</h4>
            <progress value={overallProgress} max="100" style={{ width: '100%' }}></progress>
            <p>{status.progress} of {status.total} games processed.</p>

            <hr />

            <h4>Game Status:</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid #ccc' }}>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Game</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Status</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {Object.entries(status.games).map(([game, gameStatus]) => (
                        <tr key={game} style={{ borderBottom: '1px solid #ccc' }}>
                            <td style={{ padding: '8px' }}>{game}</td>
                            <td style={{ padding: '8px' }}>{gameStatus.status}</td>
                            <td style={{ padding: '8px' }}>
                                {gameStatus.error ? <span style={{ color: 'red' }}>{gameStatus.error}</span> : 
                                 (
                                    <span>
                                        {gameStatus.ingestion && 'Ingestion ✔ '}
                                        {gameStatus.training && 'Training ✔ '}
                                        {gameStatus.prediction && 'Prediction ✔ '}
                                    </span>
                                 )
                                }
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default StartupProgress;
