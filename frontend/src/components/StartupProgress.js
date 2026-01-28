import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { analyzeError, ErrorCategory } from '../utils/errorUtils';
import ErrorMessage from './ErrorMessage';

const StartupProgress = ({ onComplete }) => {
    const [status, setStatus] = useState(null);
    const [errorReport, setErrorReport] = useState(null);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await axios.get(`${process.env.REACT_APP_API_BASE}/api/startup_status`);
                setErrorReport(null);
                setStatus(response.data);
                setElapsedSeconds(response.data.elapsed_s || 0);
                if (response.data.status === 'completed') {
                    onComplete();
                }
            } catch (error) {
                console.error("Error fetching startup status:", error);
                const report = analyzeError(error);
                setErrorReport(report);
                if (report.category === ErrorCategory.CONNECTION_ERROR) {
                    clearInterval(interval);
                }
            }
        };

        const interval = setInterval(fetchStatus, 2000);
        fetchStatus();

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
        return <div style={{ padding: '20px' }}>Initializing...</div>;
    }

    const games = status.games || {};
    const gameEntries = Object.entries(games);
    const progressVal = Number(status.progress ?? 0);
    // Fall back to the number of games if backend omits total
    const totalVal = Number(status.total ?? gameEntries.length ?? 0);
    const rowsFetched = Number(status.current_game_rows_fetched ?? 0);
    const overallProgress = totalVal > 0 ? (progressVal / totalVal) * 100 : 0;
    const isIngesting = status.status === 'ingesting';
    const isCompleted = status.status === 'completed';
    const hasGamesConfigured = gameEntries.length > 0;
    
    const formatTime = (seconds) => {
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
    };

    const getStatusIcon = (gameStatus) => {
        if (gameStatus === 'completed') return '✓';
        if (gameStatus === 'ingesting') return '↻';
        if (gameStatus === 'failed') return '✗';
        return '◯';
    };

    const getStatusColor = (gameStatus) => {
        if (gameStatus === 'completed') return '#28a745';
        if (gameStatus === 'ingesting') return '#ffc107';
        if (gameStatus === 'failed') return '#dc3545';
        return '#6c757d';
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
            <h2>🎰 Lottery Data Initialization</h2>
            
            {/* Status Header */}
            <div style={{
                padding: '15px',
                backgroundColor: isCompleted ? '#d4edda' : '#fff3cd',
                border: `2px solid ${isCompleted ? '#28a745' : '#ffc107'}`,
                borderRadius: '5px',
                marginBottom: '20px'
            }}>
                <p style={{ margin: '5px 0' }}>
                    <strong>Status:</strong> 
                    {isCompleted && <span style={{ color: '#28a745' }}>✓ Complete</span>}
                    {isIngesting && <span style={{ color: '#ffc107' }}>⟳ Downloading Game Data...</span>}
                    {!isCompleted && !isIngesting && <span>Pending</span>}
                </p>
                {status.current_game && (
                    <p style={{ margin: '5px 0' }}>
                        <strong>Currently Processing:</strong> {status.current_game.toUpperCase()}
                        {status.current_task && <span> ({status.current_task})</span>}
                    </p>
                )}
                <p style={{ margin: '5px 0' }}>
                    <strong>Elapsed Time:</strong> {formatTime(elapsedSeconds)}
                </p>
            </div>

            {/* Progress Bar */}
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ marginBottom: '8px' }}>
                    Download Progress: {progressVal.toFixed(1)} of {totalVal} games
                    {rowsFetched > 0 && (
                        <span style={{ fontSize: '0.9em', color: '#666' }}>
                            {' '}({rowsFetched.toLocaleString()} rows in {status.current_game})
                        </span>
                    )}
                </h4>
                {!hasGamesConfigured && (
                    <p style={{ marginTop: '-4px', color: '#6c757d' }}>
                        No games reported by backend yet. This usually means ingestion has not started.
                    </p>
                )}
                <div style={{
                    width: '100%',
                    backgroundColor: '#e9ecef',
                    borderRadius: '5px',
                    overflow: 'hidden',
                    height: '30px',
                    display: 'flex',
                    alignItems: 'center'
                }}>
                    <div style={{
                        width: `${overallProgress}%`,
                        backgroundColor: overallProgress === 100 ? '#28a745' : '#007bff',
                        height: '100%',
                        transition: 'width 0.3s ease',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontWeight: 'bold',
                        fontSize: '14px'
                    }}>
                        {Math.round(overallProgress)}%
                    </div>
                </div>
            </div>

            {/* Game Status Table */}
            <h4>Game Download Status</h4>
            <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                marginBottom: '20px'
            }}>
                <thead>
                    <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                        <th style={{ textAlign: 'left', padding: '12px' }}>Game</th>
                        <th style={{ textAlign: 'center', padding: '12px', width: '80px' }}>Status</th>
                        <th style={{ textAlign: 'left', padding: '12px' }}>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {gameEntries.length === 0 && (
                        <tr>
                            <td colSpan="3" style={{ padding: '12px', textAlign: 'center', color: '#6c757d' }}>
                                Waiting for backend to report game ingestion status...
                            </td>
                        </tr>
                    )}
                    {gameEntries.map(([game, gameData]) => (
                        <tr
                            key={game}
                            style={{
                                borderBottom: '1px solid #dee2e6',
                                backgroundColor: game === status.current_game ? '#f0f8ff' : 'white',
                                transition: 'background-color 0.3s ease'
                            }}
                        >
                            <td style={{ padding: '12px', fontWeight: 'bold' }}>
                                {game.charAt(0).toUpperCase() + game.slice(1)}
                            </td>
                            <td style={{
                                padding: '12px',
                                textAlign: 'center',
                                color: getStatusColor(gameData.status),
                                fontSize: '18px',
                                fontWeight: 'bold'
                            }}>
                                {getStatusIcon(gameData.status)}
                            </td>
                            <td style={{ padding: '12px' }}>
                                {gameData.status === 'completed' && (
                                    <span style={{ color: '#28a745' }}>Downloaded ✓</span>
                                )}
                                {gameData.status === 'ingesting' && (
                                    <span style={{ color: '#ffc107' }}>Downloading...</span>
                                )}
                                {gameData.status === 'pending' && (
                                    <span style={{ color: '#6c757d' }}>Waiting...</span>
                                )}
                                {gameData.status === 'failed' && (
                                    <span style={{ color: '#dc3545' }}>
                                        Failed {gameData.error && `(${gameData.error})`}
                                    </span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            {isCompleted && (
                <div style={{
                    padding: '15px',
                    backgroundColor: '#d4edda',
                    border: '2px solid #28a745',
                    borderRadius: '5px',
                    color: '#155724',
                    textAlign: 'center'
                }}>
                    <h3 style={{ margin: '10px 0' }}>✓ All games downloaded successfully!</h3>
                    <p style={{ margin: '5px 0' }}>Launching dashboard...</p>
                </div>
            )}
        </div>
    );
};

export default StartupProgress;
