// postMessage channel: widget iframe → host page.
// Only used for resize events so the host can size the iframe dynamically.
// Origin is validated on the host side in the loader script.

// Notify the host page of the iframe's new height so it can resize the container.
export function postResize(height: number): void {
  window.parent.postMessage({ type: "copilot:resize", height }, "*");
}

// Call on mount and whenever content height changes.
// Attach a ResizeObserver to an element and post resize messages whenever its height changes.
export function observeResize(element: HTMLElement): () => void {
  const observer = new ResizeObserver(() => {
    postResize(element.scrollHeight);
  });
  observer.observe(element);
  return () => observer.disconnect();
}
