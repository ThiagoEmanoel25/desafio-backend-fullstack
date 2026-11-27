interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state" role="alert">
      <p className="error">{message}</p>
      {onRetry && (
        <button type="button" className="secondary" onClick={onRetry}>
          Tentar novamente
        </button>
      )}
    </div>
  )
}
