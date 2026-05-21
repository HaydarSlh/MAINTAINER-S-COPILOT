// Loader script — host page pastes ONE tag:
//   <script src="http://widget:8080/widget.js" data-widget-id="abc123" async></script>
// This script injects the iframe and wires the resize postMessage.
(function () {
  "use strict";
  var s = document.currentScript;
  var widgetId = s && s.getAttribute("data-widget-id");
  if (!widgetId) {
    console.error("[copilot-widget] data-widget-id attribute missing on <script> tag");
    return;
  }

  var WIDGET_ORIGIN = s.src.replace(/\/widget\.js.*$/, "");

  var iframe = document.createElement("iframe");
  iframe.src = WIDGET_ORIGIN + "/index.html?widget_id=" + encodeURIComponent(widgetId);
  iframe.id = "copilot-widget-frame";
  iframe.allow = "clipboard-write";
  iframe.style.cssText = [
    "position:fixed",
    "bottom:0",
    "right:0",
    "width:400px",
    "height:80px",   // bubble height; grows on open via postMessage
    "border:none",
    "z-index:2147483647",
    "background:transparent",
  ].join(";");

  document.body.appendChild(iframe);

  // Resize channel — widget posts { type: "copilot:resize", height }
  window.addEventListener("message", function (evt) {
    if (evt.origin !== WIDGET_ORIGIN) return;
    if (!evt.data || evt.data.type !== "copilot:resize") return;
    var h = Number(evt.data.height);
    if (h > 0) iframe.style.height = h + "px";
  });
})();
