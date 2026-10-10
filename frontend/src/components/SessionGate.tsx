import { useEffect, useState, type ReactNode } from "react";
import { restoreSession, errorMessage } from "../api/client";
export default function SessionGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [error, setError] = useState("");
  function restore() {
    setStatus("loading");
    restoreSession()
      .then(() => setStatus("ready"))
      .catch((e) => {
        setError(errorMessage(e));
        setStatus("error");
      });
  }
  useEffect(() => {
    let active = true;
    restoreSession()
      .then(() => {
        if (active) setStatus("ready");
      })
      .catch((e) => {
        if (active) {
          setError(errorMessage(e));
          setStatus("error");
        }
      });
    return () => {
      active = false;
    };
  }, []);
  if (status === "loading")
    return (
      <main>
        <div className="notice" role="status">
          Открываем ваш столик…
        </div>
      </main>
    );
  if (status === "error")
    return (
      <main>
        <div className="notice" role="alert">
          {error} <button onClick={restore}>Повторить</button>
        </div>
      </main>
    );
  return children;
}
