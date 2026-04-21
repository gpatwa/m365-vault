/**
 * Postbuild prerender script for SEO.
 *
 * After `vite build`, this script:
 * 1. Serves the dist/ folder on a local port
 * 2. Uses Puppeteer to load each public route
 * 3. Waits for React to render, then captures the full HTML
 * 4. Writes static HTML files so crawlers see real content
 *
 * Usage: node scripts/prerender.mjs
 */

import { createServer } from 'http';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, extname, dirname } from 'path';
import { fileURLToPath } from 'url';
import puppeteer from 'puppeteer';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DIST = join(__dirname, '..', 'dist');
const PRERENDERED = join(__dirname, '..', 'prerendered');
const PORT = 4173;

const ROUTES = [
  '/welcome',
  '/about',
  '/tour',
  '/contact',
  '/legal',
  '/security',
  '/scenarios/compromised-global-admin',
  '/scenarios/destructive-sharepoint-onedrive-deletion',
  '/scenarios/bulk-mailbox-deletion-retention-drift',
];

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.txt': 'text/plain',
  '.xml': 'application/xml',
};

/** Minimal static file server for dist/ */
function startServer() {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      let filePath = join(DIST, req.url === '/' ? '/index.html' : req.url);

      // SPA fallback: if file doesn't exist, serve index.html
      if (!existsSync(filePath) || filePath.endsWith('/')) {
        filePath = join(DIST, 'index.html');
      }

      try {
        const content = readFileSync(filePath);
        const ext = extname(filePath);
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
        res.end(content);
      } catch {
        res.writeHead(404);
        res.end('Not found');
      }
    });

    server.listen(PORT, () => {
      console.log(`  Static server on http://localhost:${PORT}`);
      resolve(server);
    });
  });
}

async function prerender() {
  console.log('\nPrerendering landing pages for SEO...\n');

  if (!existsSync(DIST)) {
    console.error('Error: dist/ not found. Run `npm run build` first.');
    process.exit(1);
  }

  const server = await startServer();
  const browser = await puppeteer.launch({ headless: true });

  for (const route of ROUTES) {
    const page = await browser.newPage();

    // Block external requests (analytics, fonts CDN) for faster rendering
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const url = req.url();
      if (url.startsWith(`http://localhost:${PORT}`)) {
        req.continue();
      } else {
        req.abort();
      }
    });

    console.log(`  Rendering ${route} ...`);
    await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Wait for React to render content into #root
    await page.waitForFunction(
      () => (document.querySelector('#root')?.children.length ?? 0) > 0,
      { timeout: 10000 }
    );

    // Get the actual document title (Helmet sets this via document.title)
    const docTitle = await page.title();

    // Remove duplicate tags injected by Helmet (keeps the last/Helmet version)
    let html = await page.content();
    // Replace all <title> tags with the actual document.title from Helmet
    html = html.replace(/<title>[^<]*<\/title>/g, '');
    html = html.replace('</head>', `<title>${docTitle}</title></head>`);
    // Remove duplicate meta tags — keep only the last occurrence of each
    const metaNames = ['description', 'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image'];
    for (const name of metaNames) {
      const re = new RegExp(`<meta name="${name}" content="[^"]*">`, 'g');
      const matches = [...html.matchAll(re)];
      if (matches.length > 1) {
        for (let i = 0; i < matches.length - 1; i++) {
          html = html.replace(matches[i][0], '');
        }
      }
    }
    // Same for og: properties
    const ogProps = ['og:type', 'og:site_name', 'og:title', 'og:description', 'og:image'];
    for (const prop of ogProps) {
      const re = new RegExp(`<meta property="${prop}" content="[^"]*">`, 'g');
      const matches = [...html.matchAll(re)];
      if (matches.length > 1) {
        for (let i = 0; i < matches.length - 1; i++) {
          html = html.replace(matches[i][0], '');
        }
      }
    }

    // Write to both dist/ (for local preview) and prerendered/ (for Docker)
    for (const base of [DIST, PRERENDERED]) {
      const outDir = join(base, route);
      mkdirSync(outDir, { recursive: true });
      writeFileSync(join(outDir, 'index.html'), html);
    }
    console.log(`    -> ${route}/index.html (${(html.length / 1024).toFixed(1)} KB)`);

    await page.close();
  }

  await browser.close();
  server.close();

  console.log(`\nPrerendered ${ROUTES.length} pages.\n`);
}

prerender().catch((err) => {
  console.error('Prerender failed:', err);
  process.exit(1);
});
