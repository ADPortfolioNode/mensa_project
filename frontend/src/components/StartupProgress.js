import React, { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import { getApiBase } from '../utils/apiBase';
import { analyzeError, ErrorCategory } from '../utils/errorUtils';
import ErrorMessage from './ErrorMessage';
import ProgressiveProgressBar from './ProgressiveProgressBar';

const StartupProgress = ({ onComplete }) => {
    const apiBase = getApiBase();
    const [status, setStatus] = useState(null);
    const [errorReport, setErrorReport] = useState(null);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const [isStarting, setIsStarting] = useState(false);
    const transientErrorCountRef = useRef(0);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await axios.get(`${apiBase}/api/startup_status`);
                transientErrorCountRef.current = 0;
                setErrorReport(null);
                setStatus(response.data);
                setElapsedSeconds(response.data.elapsed_s || 0);
                // Complete on either 'completed' (auto-ingestion) or 'ready' (manual mode)
                if (response.data.status === 'completed' || response.data.status === 'ready') {
                    onComplete();
                }
            } catch (error) {
                const report = analyzeError(error);
                const statusCode = error?.response?.status;
                const isTransientGateway = statusCode === 502 || statusCode === 503 || statusCode === 504;
                const isConnectionIssue = report.category === ErrorCategory.CONNECTION_ERROR;

                if (isTransientGateway || isConnectionIssue) {
                    transientErrorCountRef.current += 1;
                    if (transientErrorCountRef.current >= 5) {
                        setErrorReport(report);
                    } else {
                        setErrorReport(null);
                    }
                    return;
                }

                console.error("Error fetching startup status:", error);
                setErrorReport(report);
                clearInterval(interval);
            }
        };

        const interval = setInterval(fetchStatus, 2000);
        fetchStatus();

        return () => clearInterval(interval);
    }, [onComplete, apiBase]);

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

    const {
        gameEntries,
        progressVal,
        totalVal,
        rowsFetched,
        isIngesting,
        isCompleted,
        isReady,
        hasGamesConfigured,
    } = useMemo(() => {
        const availableGames = Array.isArray(status.available_games) ? status.available_games : [];
        const games = status.games || {};
        const normalizedGames = availableGames.length > 0
            ? availableGames.reduce((acc, game) => {
                acc[game] = {
                    status: games?.[game]?.status || 'pending',
                    error: games?.[game]?.error || null,
                };
                return acc;
            }, {})
            : games;

        const entries = Object.entries(normalizedGames);
        const progress = Number(status.progress ?? 0);
        const total = Number(status.total ?? entries.length ?? 0);
        const fetched = Number(status.current_game_rows_fetched ?? 0);

        return {
            gameEntries: entries,
            progressVal: progress,
            totalVal: total,
            rowsFetched: fetched,
            isIngesting: status.status === 'ingesting',
            isCompleted: status.status === 'completed',
            isReady: status.status === 'ready',
            hasGamesConfigured: entries.length > 0,
        };
    }, [status]);
    
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

    const formatGameLabel = (game) => game
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());

    const handleStartInitialization = async () => {
        setIsStarting(true);
        try {
            await axios.post(`${apiBase}/api/startup_init`);
        } catch (error) {
            console.error("Error starting initialization:", error);
        } finally {
            setIsStarting(false);
        }
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
            <h2>🎰 Lottery Data Initialization</h2>
            {(isReady || status.status === 'pending') && (
                <div style={{ marginBottom: '12px' }}>
                    <button
                        onClick={handleStartInitialization}
                        disabled={isStarting}
                        style={{
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            padding: '8px 12px',
                            borderRadius: '4px',
                            cursor: isStarting ? 'not-allowed' : 'pointer'
                        }}
                    >
                        {isStarting ? 'Starting...' : 'Start Initialization'}
                    </button>
                </div>
            )}
            
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
                <ProgressiveProgressBar
                    current={progressVal}
                    total={totalVal || 1}
                    status={isCompleted ? 'completed' : isIngesting ? 'active' : 'idle'}
                    label="Overall Initialization"
                    showMetadata={true}
                    colorScheme="primary"
                />

                {hasGamesConfigured && (
                    <div style={{ marginTop: '10px' }}>
                        {gameEntries.map(([game, gameData]) => {
                            const gameStatus = gameData.status === 'failed'
                                ? 'error'
                                : gameData.status === 'ingesting'
                                    ? 'active'
                                    : gameData.status === 'completed'
                                        ? 'completed'
                                        : 'idle';

                            const gameCurrent = gameStatus === 'completed' || gameStatus === 'error' ? 1 : 0;

                            return (
                                <ProgressiveProgressBar
                                    key={`${game}-progress`}
                                    current={gameCurrent}
                                    total={1}
                                    status={gameStatus}
                                    label={formatGameLabel(game)}
                                    showMetadata={false}
                                    colorScheme="primary"
                                    indeterminate={gameStatus === 'active'}
                                />
                            );
                        })}
                    </div>
                )}
                {hasGamesConfigured && (
                    <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '8px',
                        marginTop: '10px'
                    }}>
                        {gameEntries.map(([game, gameData]) => (
                            <div
                                key={game}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    padding: '4px 10px',
                                    borderRadius: '999px',
                                    border: `1px solid ${getStatusColor(gameData.status)}`,
                                    backgroundColor: game === status.current_game ? '#f0f8ff' : '#ffffff',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                    color: '#212529'
                                }}
                            >
                                <span style={{ color: getStatusColor(gameData.status) }}>{getStatusIcon(gameData.status)}</span>
                                <span>{formatGameLabel(game)}</span>
                            </div>
                        ))}
                    </div>
                )}
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
                                {formatGameLabel(game)}
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
