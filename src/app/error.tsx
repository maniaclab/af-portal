"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section>
      <div className="container text-center">
        <h1 className="display-6 my-4">500 Internal Server Error</h1>
        <p>Something went wrong on our end.</p>
        <button className="btn btn-primary" onClick={reset}>
          Try again
        </button>
      </div>
    </section>
  );
}
