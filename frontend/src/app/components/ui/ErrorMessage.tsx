import './ErrorMessage.scss';

interface ErrorMessageProps {
  error: string;
  fullPage?: boolean;
  onRetry?: () => void;
}

export default function ErrorMessage({ error, fullPage = false, onRetry }: ErrorMessageProps) {
  const retryButton = onRetry ? (
    <button className="error-retry-btn" onClick={onRetry}>Try again</button>
  ) : null;

  if (fullPage) {
    return (
      <div className="error-container" role="alert" aria-live="assertive">
        <div className="error-content">
          <p className="error-message">{error}</p>
          <p className="error-description">Something went wrong :/</p>
          {retryButton}
        </div>
      </div>
    );
  }

  return (
    <div className="error-content" role="alert" aria-live="assertive">
      <p className="error-message">{error}</p>
      <p className="error-description">Something went wrong :/</p>
      {retryButton}
    </div>
  );
}