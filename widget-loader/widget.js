// Loader script served from /widget.js (via the `widget` service / api).
//
// The host pastes ONE tag:  <script src="https://.../widget.js"
//                                    data-widget-id="..."></script>
// This script reads data-widget-id, injects an <iframe> pointing at the React
// widget bundle, and wires the postMessage channel (at minimum iframe resize).
// Whether the embed is allowed is enforced server-side by the embed route's
// CSP frame-ancestors + CORS allowlist (from the widget's allowed_origins).

// TODO: read data-widget-id, inject iframe, listen for resize postMessage
(function () {
  /* TODO */
})();
