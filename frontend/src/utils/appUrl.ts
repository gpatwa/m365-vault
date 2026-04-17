/**
 * Hostname-aware URL helper for cross-host navigation.
 *
 * KavachIQ is split across two hosts:
 *   kavachiq.com      → marketing (Cloudflare Pages, static HTML)
 *   app.kavachiq.com  → authenticated React SPA (Azure Container Apps)
 *
 * Marketing pages need "Sign In" links to jump to the app host (full page nav).
 * The app itself and local dev should use relative paths for fast SPA navigation.
 *
 * Usage:
 *   <a href={appUrl('/login')}>Sign In</a>
 *   <a href={appUrl('/login?register=true')}>Start Free</a>
 */

const APP_HOST = 'https://app.kavachiq.com';
const MARKETING_HOSTNAME = 'kavachiq.com';

/**
 * Returns a full URL to the app host when running on the marketing site,
 * or a relative path otherwise (for SPA navigation or local dev).
 */
export function appUrl(path: string): string {
  // SSR / prerender: return relative (hydration will re-evaluate client-side)
  if (typeof window === 'undefined') return path;
  if (window.location.hostname === MARKETING_HOSTNAME) return `${APP_HOST}${path}`;
  return path;
}
