import { AlertTriangle, Inbox, Loader2, Lock } from "lucide-react";

// Non-happy states are mandatory on every list and table (H.6.2). Copy follows
// H.6.1: errors say what went wrong and how to fix it; empty states invite an
// action rather than announcing "No data". None of these carry signal colour.

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-muted" role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{label}...</span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center text-muted">
      <Inbox className="h-6 w-6" aria-hidden="true" />
      <p className="text-text">{title}</p>
      {hint ? <p className="text-sm">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-start gap-2 py-8 text-muted" role="alert">
      <div className="flex items-center gap-2 text-text">
        <AlertTriangle className="h-4 w-4" aria-hidden="true" />
        <span>{message}</span>
      </div>
      {onRetry ? (
        <button className="text-sm underline hover:text-text" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function PermissionState({ action }: { action: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center text-muted">
      <Lock className="h-6 w-6" aria-hidden="true" />
      <p className="text-text">Your role cannot {action}.</p>
      <p className="text-sm">Ask an owner or admin if you need access.</p>
    </div>
  );
}
