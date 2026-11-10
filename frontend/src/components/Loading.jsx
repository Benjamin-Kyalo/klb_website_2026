export default function Loading({ label = "Loading…", compact = false }) {
  return (
    <div className={compact ? "klb-loading klb-loading--compact" : "klb-loading"} role="status" aria-live="polite">
      <span className="klb-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "We could not load this page." }) {
  const message =
    error?.status === 404
      ? "The page or item you asked for could not be found."
      : error?.message || "Please check that the API server is running and try again.";

  return (
    <div className="klb-error" role="alert">
      <p className="kicker">Something went wrong</p>
      <h1>{title}</h1>
      <p>{message}</p>
      {onRetry ? (
        <button className="btn btn--primary" type="button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}
