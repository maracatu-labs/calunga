import { useCallback, useRef } from "react";

/**
 * Shared auto-scroll behavior for the chat message list.
 *
 * Scrolls the container itself (`scrollTop = scrollHeight`) instead of
 * `Element.scrollIntoView()`. On iOS Safari `scrollIntoView` inside a nested
 * scroll container frequently scrolls the wrong ancestor (the whole page),
 * especially while the soft keyboard is open.
 *
 * `userScrolledUp` is tracked so we never yank the viewport down while the
 * user is reading earlier messages. Callers re-enable auto-scroll with
 * `resetScroll()` whenever a new response begins.
 */
export function useAutoScroll() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);

  const scrollToBottom = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el || userScrolledUp.current) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    userScrolledUp.current = !atBottom;
  }, []);

  const resetScroll = useCallback(() => {
    userScrolledUp.current = false;
  }, []);

  return { scrollContainerRef, handleScroll, scrollToBottom, resetScroll };
}
