/**
 * Build the marketing bundle for Cloudflare Pages.
 *
 * Output: dist-marketing/
 *   - Full Vite build output (assets, index.html fallback)
 *   - Prerendered pages overlaid (welcome, about, tour, contact, legal)
 *   - _redirects file (CF Pages format) — app routes redirect to app.kavachiq.com
 *
 * Assumes `npm run build:seo` has already been run (produces dist/ + prerendered/).
 */

import { cpSync, rmSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const DIST = join(ROOT, 'dist');
const PRERENDERED = join(ROOT, 'prerendered');
const OUT = join(ROOT, 'dist-marketing');

const APP_HOST = 'https://app.kavachiq.com';

// Routes that should redirect from the marketing site to the app
const APP_ROUTES = [
  '/login', '/sso/callback', '/reset-password', '/verify-email',
  '/dashboard', '/exchange', '/onedrive', '/sharepoint', '/teams', '/entra-id',
  '/sla-policies', '/jobs', '/tenants', '/settings', '/msp', '/features',
  '/audit', '/failed-items', '/alerts', '/search', '/ediscovery',
  '/smart-engine', '/agent-shield', '/restore', '/recovery', '/reports',
  '/usage', '/billing', '/security-posture', '/security', '/performance',
  '/org-context', '/onboard',
];

function build() {
  console.log('\nBuilding marketing bundle for Cloudflare Pages...\n');

  if (!existsSync(DIST)) {
    console.error('Error: dist/ not found. Run `npm run build:seo` first.');
    process.exit(1);
  }
  if (!existsSync(PRERENDERED)) {
    console.error('Error: prerendered/ not found. Run `npm run build:seo` first.');
    process.exit(1);
  }

  // 1. Clean output
  if (existsSync(OUT)) rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });

  // 2. Copy dist/ → dist-marketing/ (full Vite output: assets, fallback index.html)
  console.log('  Copying dist/ → dist-marketing/');
  cpSync(DIST, OUT, { recursive: true });

  // 3. Overlay prerendered/ → dist-marketing/ (per-page index.html with SEO)
  console.log('  Overlaying prerendered/ → dist-marketing/');
  cpSync(PRERENDERED, OUT, { recursive: true });

  // 4. Write _redirects for Cloudflare Pages.
  //
  // CRITICAL: CF Pages evaluates _redirects BEFORE serving static files.
  // That means a `/*` catchall will intercept even /welcome, /about, etc.
  // So we only list explicit app-route redirects. Unknown routes 404 naturally.
  //
  // Also: CF Pages auto-redirects /path -> /path/ when /path/index.html exists.
  // Our prerendered HTML lives at /welcome/index.html etc., so /welcome -> /welcome/ -> serves.
  console.log('  Writing _redirects');
  const lines = [
    '# Redirect root to marketing landing',
    '/                    /welcome/             301',
    '',
    '# App routes -> app.kavachiq.com (authenticated SPA lives there)',
  ];
  for (const route of APP_ROUTES) {
    lines.push(`${route.padEnd(20)} ${APP_HOST}${route}   301`);
    lines.push(`${(route + '/*').padEnd(20)} ${APP_HOST}${route}/:splat   301`);
  }
  lines.push('');
  lines.push('# Docs -> app.kavachiq.com');
  lines.push('/docs                ' + APP_HOST + '/docs   301');
  lines.push('/docs/*              ' + APP_HOST + '/docs/:splat   301');
  lines.push('');
  lines.push('# No catchall — unknown paths 404 (SEO-correct for marketing)');
  writeFileSync(join(OUT, '_redirects'), lines.join('\n') + '\n');

  // 5. Summary
  console.log('\nMarketing bundle ready: dist-marketing/');
  console.log('  Deploy with: npm run pages:deploy\n');
}

build();
