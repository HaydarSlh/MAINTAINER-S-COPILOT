// Bootstrap: read widget_id from URL, fetch public config, mount Widget.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { fetchConfig } from "./api";
import { Widget } from "./Widget";

// Initialize the widget by reading the widget_id from the URL, fetching config, and mounting the React app.
async function boot() {
  const params = new URLSearchParams(window.location.search);
  const widgetId = params.get("widget_id") ?? window.location.pathname.split("/").pop() ?? "";

  if (!widgetId) {
    console.error("[copilot-widget] widget_id not found in URL");
    return;
  }

  let config;
  try {
    config = await fetchConfig(widgetId);
  } catch (err) {
    console.error("[copilot-widget] failed to load config:", err);
    return;
  }

  const root = document.getElementById("root");
  if (!root) return;

  createRoot(root).render(
    <StrictMode>
      <Widget config={config} widgetId={widgetId} />
    </StrictMode>,
  );
}

boot();
