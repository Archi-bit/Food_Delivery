import type { ReactNode } from "react";
import { errorMessage } from "../api/client";
export function State({
  loading,
  error,
  children,
}: {
  loading?: boolean;
  error?: unknown;
  children: ReactNode;
}) {
  if (loading)
    return (
      <div aria-label="Загрузка" className="skeleton-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton" />
        ))}
      </div>
    );
  if (error)
    return (
      <div role="alert" className="notice">
        {errorMessage(error)}{" "}
        <button onClick={() => location.reload()}>Повторить</button>
      </div>
    );
  return <>{children}</>;
}
export function Image({ src, alt }: { src: string | null; alt: string }) {
  return src ? (
    <img loading="lazy" src={src} alt={alt} />
  ) : (
    <div className="placeholder" role="img" aria-label={alt}>
      🍲
    </div>
  );
}
