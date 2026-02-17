import React from 'react';

const ErrorMessage = ({ errorReport }) => {
    if (!errorReport) {
        return null;
    }

    return (
        <div className="alert alert-danger my-3 app-error-message">
            <h4 className="mt-0">{errorReport.title}</h4>
            <p><strong>Details:</strong> {errorReport.originalError}</p>
            <p><strong>Suggestions:</strong></p>
            <ul>
                {errorReport.suggestions.map((suggestion, index) => (
                    <li key={index}>{suggestion}</li>
                ))}
            </ul>
        </div>
    );
};

export default ErrorMessage;
