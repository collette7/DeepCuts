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

  const content = (
    <div className="error-content" role="alert" aria-live="assertive">
      <p className="error-message">{error}</p>
      {retryButton}
    </div>
  );

  if (fullPage) {
    return (
      <div className="error-container">
        {content}
      </div>
    );
  }

  return content;
}