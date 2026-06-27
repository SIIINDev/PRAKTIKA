interface EmptyStateProps {
  icon?: string;
  title?: string;
  message: string;
  testId?: string;
}

export function EmptyState({ icon = "🔍", title, message, testId }: EmptyStateProps) {
  return (
    <div className="state" data-testid={testId} role="status">
      <span className="state-icon" aria-hidden="true">
        {icon}
      </span>
      {title ? <div className="state-title">{title}</div> : null}
      <div>{message}</div>
    </div>
  );
}
