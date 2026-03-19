import './LoadingSpinner.scss';

interface LoadingSpinnerProps {
  fullPage?: boolean;
}

export default function LoadingSpinner({ fullPage = false }: LoadingSpinnerProps) {
  if (fullPage) {
    return (
      <div className="loading-container" role="status" aria-live="polite">
        <div className="loading-content">
          <div className="loading-spinner" aria-hidden="true"></div>
          <p className="loading-text">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="loading-content" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true"></div>
      <p className="loading-text">Loading...</p>
    </div>
  );
}