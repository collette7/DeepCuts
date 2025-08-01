interface ErrorMessageProps {
  error: string;
  fullPage?: boolean;
}

export default function ErrorMessage({ error, fullPage = false }: ErrorMessageProps) {
  if (fullPage) {
    return (
      <div className="error-container">
        <div className="error-content">
          <p className="error-message">{error}</p>
          <p className="error-description">Something went wrong :/</p>
        </div>
      </div>
    );
  }

  return (
    <div className="error-content">
      <p className="error-message">{error}</p>
      <p className="error-description">Something went wrong :/</p>
    </div>
  );
}