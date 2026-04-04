// Shieldio Runtime Config — injected by nginx in Docker/Azure
// Override these values via environment variables in production

// PostHog Analytics (product analytics, session replay, heatmaps)
window.__POSTHOG_KEY = "phc_oYDV4eh9EXyME3X8fhe77vhw4hvjFfFw2u6bjhLknSMs";
window.__POSTHOG_HOST = "https://us.i.posthog.com";

// API base URL (overridden by nginx proxy in Docker)
// window.__API_BASE = "/api";
