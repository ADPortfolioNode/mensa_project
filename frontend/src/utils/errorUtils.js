export const ErrorCategory = {
    CONNECTION_ERROR: 'CONNECTION_ERROR',
    UNKNOWN_ERROR: 'UNKNOWN_ERROR',
};

const errorPatterns = {
    [ErrorCategory.CONNECTION_ERROR]: [
        /network error/i,
        /connection refused/i,
        /connection reset/i,
        /connection was closed/i,
        /empty response/i,
        /502 bad gateway/i,
        /503 service unavailable/i,
        /504 gateway timeout/i,
        /timeout of \d+ms exceeded/i,
        /ECONNABORTED/i,
    ],
};

/** Turn axios/FastAPI errors into readable text (handles detail arrays). */
export function formatApiError(error, fallback = 'Request failed') {
    const data = error?.response?.data;
    if (!data) {
        return error?.message || fallback;
    }

    const detail = data.detail ?? data.message ?? data.error;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                if (item == null) return '';
                if (typeof item === 'string') return item;
                if (typeof item === 'object') {
                    const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : '';
                    const msg = item.msg || item.message || JSON.stringify(item);
                    return loc ? `${loc}: ${msg}` : msg;
                }
                return String(item);
            })
            .filter(Boolean)
            .join('; ');
    }

    if (detail && typeof detail === 'object') {
        return detail.message || detail.msg || JSON.stringify(detail);
    }

    return String(detail || error?.message || fallback);
}

export function analyzeError(error) {
    const errorMessage = error.message || String(error);

    let category = ErrorCategory.UNKNOWN_ERROR;
    for (const [cat, patterns] of Object.entries(errorPatterns)) {
        if (patterns.some(pattern => pattern.test(errorMessage))) {
            category = cat;
            break;
        }
    }

    const titles = {
        [ErrorCategory.CONNECTION_ERROR]: "Connection Issue",
        [ErrorCategory.UNKNOWN_ERROR]: "Unexpected Error",
    };

    const suggestions = {
        [ErrorCategory.CONNECTION_ERROR]: [
            "Wait 60-90 seconds after a container restart, then hard-refresh (Ctrl+Shift+R).",
            "Try http://127.0.0.1:3000 instead of http://localhost:3000 (Windows IPv6/Docker issue).",
            "Restart Docker Desktop, then run: docker compose up -d --force-recreate",
            "Check containers: docker ps --filter name=mensa",
            "Review backend logs: docker logs mensa_backend --tail 50",
        ],
        [ErrorCategory.UNKNOWN_ERROR]: [
            "Check the browser console for more details.",
            "Try refreshing the page.",
            "Report this issue if it persists.",
        ],
    };

    return {
        category,
        title: titles[category],
        originalError: errorMessage,
        suggestions: suggestions[category],
    };
}
