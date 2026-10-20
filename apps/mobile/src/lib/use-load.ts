/**
 * Load data for a screen, again when `key` changes or on `reload()`, tracking failure so the screen
 * can show the offline edge state. The latest `load` is used without being a dependency.
 */
import { useEffect, useRef, useState } from "react";

export function useLoad<T>(load: () => Promise<T>, key = "") {
  const [data, setData] = useState<T | null>(null);
  const [failed, setFailed] = useState(false);
  const [nonce, setNonce] = useState(0);
  const latest = useRef(load);

  useEffect(() => {
    latest.current = load;
  });

  useEffect(() => {
    let live = true;
    latest
      .current()
      .then((d) => live && setData(d))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [key, nonce]);

  function reload() {
    setFailed(false);
    setNonce((n) => n + 1);
  }

  return { data, failed, reload, setData };
}
