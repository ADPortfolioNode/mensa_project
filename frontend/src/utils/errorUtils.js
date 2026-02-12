export const ErrorCategory = {
    CONNECTION_ERROR: 'CONNECTION_ERROR',
    UNKNOWN_ERROR: 'UNKNOWN_ERROR',
};

const errorPatterns = {
    [ErrorCategory.CONNECTION_ERROR]: [
        /network error/i,
        /connection refused/i,
        /502 bad gateway/i,
    ],
};

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
            "Check if the backend service is running.",
            "Review the backend logs for startup errors.",
            "Ensure the backend is accessible at http://localhost:5000.",
            "Check for firewall rules blocking the connection.",
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
