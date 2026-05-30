"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Reveals `text` progressively for a typewriter effect while `enabled`.
 *
 * The streamed answer already arrives token by token; this smooths it into a
 * steady character reveal so the text "types" instead of appearing in bursts.
 * It always trails the latest target (kept in a ref) and catches up, so it never
 * falls far behind a fast stream. When `enabled` is false (history, finished
 * messages) it returns the full text immediately, no animation.
 */
export function useTypewriter(text: string, enabled: boolean): string {
  const [shown, setShown] = useState(enabled ? "" : text);
  const targetRef = useRef(text);
  targetRef.current = text;

  useEffect(() => {
    if (!enabled) {
      setShown(targetRef.current);
      return;
    }
    const id = setInterval(() => {
      setShown((prev) => {
        const target = targetRef.current;
        if (prev.length >= target.length) {
          // Caught up (or target shrank): keep the same reference so React bails
          // out of re-rendering between tokens.
          return prev.length === target.length ? prev : target;
        }
        const remaining = target.length - prev.length;
        const step = Math.max(3, Math.ceil(remaining / 7));
        return target.slice(0, prev.length + step);
      });
    }, 24);
    return () => clearInterval(id);
  }, [enabled]);

  return enabled ? shown : text;
}
