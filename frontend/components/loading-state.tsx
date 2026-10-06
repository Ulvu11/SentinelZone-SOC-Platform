export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center py-16"
    >
      <div className="w-8 h-8 border-2 border-soc-line border-t-soc-accent rounded-full animate-spin mb-4" />
      <p className="text-sm text-soc-muted">{message}</p>
    </div>
  );
}
