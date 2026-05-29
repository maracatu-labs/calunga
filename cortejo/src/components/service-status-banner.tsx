"use client";

import { useEffect, useState } from "react";
import { CloudOff } from "lucide-react";

// Polls /api/health every 30s and surfaces a banner when the backend is
// unreachable. Detection is best-effort: we only show the banner after two
// consecutive failures to avoid flicker on transient blips.

const POLL_INTERVAL_MS = 30_000;
const FAIL_THRESHOLD = 2;

export default function ServiceStatusBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let failures = 0;

    async function check() {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        if (cancelled) return;
        if (res.ok) {
          failures = 0;
          setOffline(false);
        } else {
          failures += 1;
          if (failures >= FAIL_THRESHOLD) setOffline(true);
        }
      } catch {
        if (cancelled) return;
        failures += 1;
        if (failures >= FAIL_THRESHOLD) setOffline(true);
      }
    }

    check();
    const id = setInterval(check, POLL_INTERVAL_MS);

    function onOnline() { check(); }
    function onOffline() { setOffline(true); }
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);

    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-0 inset-x-0 z-[100] bg-amber-500 text-amber-950 px-4 py-2 text-sm font-medium flex items-center justify-center gap-2 shadow"
    >
      <CloudOff className="w-4 h-4" aria-hidden />
      <span>
        Estamos com instabilidade no servidor. Algumas ações podem não funcionar até voltarmos.
      </span>
    </div>
  );
}
