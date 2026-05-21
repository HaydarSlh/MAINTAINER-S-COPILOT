// postMessage channel: widget iframe → host page.
// Only used for resize events so the host can size the iframe dynamically.
// Origin is validated on the host side in the loader script.

export function postResize(height: number): void {
  window.parent.postMessage({ type: "copilot:resize", height }, "*");
}

// Call on mount and whenever content height changes.
export function observeResize(element: HTMLElement): () => void {
  const observer = new ResizeObserver(() => {
    postResize(element.scrollHeight);
  });
  observer.observe(element);
  return () => observer.disconnect();
}
