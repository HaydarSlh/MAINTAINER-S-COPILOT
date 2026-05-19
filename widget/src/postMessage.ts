// The single postMessage channel between widget (in iframe) and host page.
// At minimum: iframe resize messages so the host can size the embed. Origin
// is validated on both ends.

// TODO: postResize(height), and host-side handler lives in the loader script
export {};
