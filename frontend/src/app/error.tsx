"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
        Something went wrong
      </h1>
      <p className="text-sm text-[var(--gray-text)]">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110"
      >
        Try again
      </button>
    </main>
  );
}
