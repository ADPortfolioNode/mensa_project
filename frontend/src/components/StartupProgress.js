import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { getApiBase } from '../utils/apiBase';
import { analyzeError, ErrorCategory } from '../utils/errorUtils';
import ErrorMessage from './ErrorMessage';

const StartupProgress = ({ onComplete }) => {
    const [status, setStatus] = useState(null);
    const [errorReport, setErrorReport] = useState(null);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const [isStarting, setIsStarting] = useState(false);
    const transientErrorCountRef = useRef(0);

    const getStartupStatus = async () => {
        const apiBase = getApiBase();
        const primaryUrl = `${apiBase}/api/startup_status`;
        const fallbackUrl = apiBase
            ? null
            : `${window.location.protocol}//${window.location.hostname}:5000/api/startup_status`;

        try {
            return await axios.get(primaryUrl, { timeout: 10000 });
        } catch (primaryError) {
            if (!fallbackUrl) throw primaryError;
            return axios.get(fallbackUrl, { timeout: 10000 });
        }
    };

    const postStartupInit = async () => {
        const apiBase = getApiBase();
        const primaryUrl = `${apiBase}/api/startup_init`;
        const fallbackUrl = apiBase
            ? null
            : `${window.location.protocol}//${window.location.hostname}:5000/api/startup_init`;

        try {
            return await axios.post(primaryUrl, null, { timeout: 10000 });
        } catch (primaryError) {
            if (!fallbackUrl) throw primaryError;
            return axios.post(fallbackUrl, null, { timeout: 10000 });
        }
    };

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await getStartupStatus();
                transientErrorCountRef.current = 0;
                setErrorReport(null);
                setStatus(response.data);
                setElapsedSeconds(response.data.elapsed_s || 0);
                // Complete when backend is either fully initialized or in ready/manual mode.
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
    }, [onComplete]);

    if (errorReport) {
        return (
            <div className="container py-4">
                <ErrorMessage errorReport={errorReport} />
            </div>
        );
    }

    if (!status || status.status === 'pending') {
        return <div className="container py-4">Initializing...</div>;
    }

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
    const gameEntries = Object.entries(normalizedGames);
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

    const getStatusTextClass = (gameStatus) => {
        if (gameStatus === 'completed') return 'text-success';
        if (gameStatus === 'ingesting') return 'text-warning';
        if (gameStatus === 'failed') return 'text-danger';
        return 'text-secondary';
    };

    const getGameStatusClass = (gameStatus) => {
        if (gameStatus === 'completed') return 'status-completed';
        if (gameStatus === 'ingesting') return 'status-ingesting';
        if (gameStatus === 'failed') return 'status-failed';
        return 'status-pending';
    };

    const formatGameLabel = (game) => game
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());

    const handleStartInitialization = async () => {
        setIsStarting(true);
        try {
            await postStartupInit();
        } catch (error) {
            console.error("Error starting initialization:", error);
        } finally {
            setIsStarting(false);
        }
    };

    return (
        <div className="container py-4 startup-shell">
            <h2 className="mb-3">🎰 Lottery Data Initialization</h2>
            {status.status === 'pending' && (
                <div className="mb-3">
                    <button
                        onClick={handleStartInitialization}
                        disabled={isStarting}
                        className="btn btn-primary"
                    >
                        {isStarting ? 'Starting...' : 'Start Initialization'}
                    </button>
                </div>
            )}
            
            {/* Status Header */}
            <div className={`card startup-status-card mb-4 ${isCompleted ? 'is-complete' : isIngesting ? 'is-active' : ''}`}>
                <div className="card-body">
                <p className="mb-2">
                    <strong>Status:</strong> 
                    {isCompleted && <span className="text-success ms-2">✓ Complete</span>}
                    {isIngesting && <span className="text-warning ms-2">⟳ Downloading Game Data...</span>}
                    {!isCompleted && !isIngesting && <span className="ms-2">Ready</span>}
                </p>
                {status.current_game && (
                    <p className="mb-2">
                        <strong>Currently Processing:</strong> {status.current_game.toUpperCase()}
                        {status.current_task && <span> ({status.current_task})</span>}
                    </p>
                )}
                <p className="mb-0">
                    <strong>Elapsed Time:</strong> {formatTime(elapsedSeconds)}
                </p>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
                <h4 className="mb-2">
                    Download Progress: {progressVal.toFixed(1)} of {totalVal} games
                    {rowsFetched > 0 && (
                        <span className="small text-muted">
                            {' '}({rowsFetched.toLocaleString()} rows in {status.current_game})
                        </span>
                    )}
                </h4>
                {!hasGamesConfigured && (
                    <p className="text-muted mb-2">
                        No games reported by backend yet. This usually means ingestion has not started.
                    </p>
                )}
                <div className="progress startup-progress-bar">
                    <progress
                        className={`startup-progress-native ${overallProgress === 100 ? 'is-complete' : 'is-active'}`}
                        value={Math.max(0, Math.min(overallProgress, 100))}
                        max="100"
                    />
                    <span className="startup-progress-overlay">{Math.round(overallProgress)}%</span>
                </div>
                {hasGamesConfigured && (
                    <div className="d-flex flex-wrap gap-2 mt-2">
                        {gameEntries.map(([game, gameData]) => (
                            <div
                                key={game}
                                className={`startup-game-pill ${getGameStatusClass(gameData.status)} ${game === status.current_game ? 'is-current' : ''}`}
                            >
                                <span className={getStatusTextClass(gameData.status)}>{getStatusIcon(gameData.status)}</span>
                                <span>{formatGameLabel(game)}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Game Status Table */}
            <h4>Game Download Status</h4>
            <div className="table-responsive mb-4">
            <table className="table table-hover align-middle startup-status-table">
                <thead>
                    <tr>
                        <th>Game</th>
                        <th className="text-center startup-status-col">Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {gameEntries.length === 0 && (
                        <tr>
                            <td colSpan="3" className="text-center text-muted py-3">
                                Waiting for backend to report game ingestion status...
                            </td>
                        </tr>
                    )}
                    {gameEntries.map(([game, gameData]) => (
                        <tr
                            key={game}
                            className={game === status.current_game ? 'startup-current-row' : ''}
                        >
                            <td className="fw-semibold">
                                {formatGameLabel(game)}
                            </td>
                            <td className={`text-center fs-5 fw-bold ${getStatusTextClass(gameData.status)}`}>
                                {getStatusIcon(gameData.status)}
                            </td>
                            <td>
                                {gameData.status === 'completed' && (
                                    <span className="text-success">Downloaded ✓</span>
                                )}
                                {gameData.status === 'ingesting' && (
                                    <span className="text-warning">Downloading...</span>
                                )}
                                {gameData.status === 'pending' && (
                                    <span className="text-secondary">Waiting...</span>
                                )}
                                {gameData.status === 'failed' && (
                                    <span className="text-danger">
                                        Failed {gameData.error && `(${gameData.error})`}
                                    </span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>

            {isCompleted && (
                <div className="alert alert-success text-center startup-complete-banner">
                    <h3 className="my-2">✓ All games downloaded successfully!</h3>
                    <p className="mb-0">Launching dashboard...</p>
                </div>
            )}
        </div>
    );
};

export default StartupProgress;
