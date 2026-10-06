"use client";
import { ErrorState } from "@/components/error-state";
export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorState
      title="Unable to load this workspace"
      message="The data service could not complete the request. Retry to reconnect."
      onRetry={reset}
    />
  );
}
