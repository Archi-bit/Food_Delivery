import { useEffect, useState } from "react";
import { authenticated } from "../api/client";
export function useAuth() {
  const [value, setValue] = useState(authenticated);
  useEffect(() => {
    const update = () => setValue(authenticated());
    window.addEventListener("auth-change", update);
    return () => window.removeEventListener("auth-change", update);
  }, []);
  return value;
}
