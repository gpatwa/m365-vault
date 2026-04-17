/**
 * Generate OG image (1200x630) for social sharing previews.
 * Uses Puppeteer to render an HTML template to PNG.
 */

import { writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import puppeteer from 'puppeteer';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT = join(__dirname, '..', 'public', 'og-image.jpg');

const html = `<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px;
    height: 630px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
  }

  /* Subtle grid pattern */
  body::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(45,212,191,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(45,212,191,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  /* Glow effect */
  .glow {
    position: absolute;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(45,212,191,0.12) 0%, transparent 70%);
    top: -100px;
    right: -100px;
  }
  .glow-2 {
    position: absolute;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%);
    bottom: -80px;
    left: -80px;
  }

  .content {
    position: relative;
    z-index: 1;
    text-align: center;
    padding: 0 80px;
  }

  .logo-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin-bottom: 32px;
  }

  .shield {
    width: 48px;
    height: 48px;
  }

  .logo-text {
    font-size: 32px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.5px;
  }

  h1 {
    font-size: 56px;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -1.5px;
    margin-bottom: 20px;
  }
  h1 .white { color: #f1f5f9; }
  h1 .teal { color: #2dd4bf; }

  .subtitle {
    font-size: 22px;
    color: #94a3b8;
    line-height: 1.5;
    max-width: 800px;
    margin: 0 auto 36px;
  }

  .badges {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .badge {
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
  }
  .badge-teal {
    background: rgba(45,212,191,0.15);
    color: #2dd4bf;
    border: 1px solid rgba(45,212,191,0.25);
  }
  .badge-cyan {
    background: rgba(34,211,238,0.12);
    color: #22d3ee;
    border: 1px solid rgba(34,211,238,0.2);
  }
  .badge-slate {
    background: rgba(148,163,184,0.1);
    color: #94a3b8;
    border: 1px solid rgba(148,163,184,0.2);
  }

  .footer {
    position: absolute;
    bottom: 28px;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 15px;
    color: #475569;
    letter-spacing: 0.3px;
  }
</style>
</head>
<body>
  <div class="glow"></div>
  <div class="glow-2"></div>

  <div class="content">
    <div class="logo-row">
      <svg class="shield" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
      <span class="logo-text">KavachIQ</span>
    </div>

    <h1>
      <span class="white">Microsoft 365 Backup &</span><br>
      <span class="teal">Ransomware Recovery</span>
    </h1>

    <p class="subtitle">
      Identity-first recovery for Exchange, OneDrive, SharePoint, Teams & Entra ID
    </p>

    <div class="badges">
      <span class="badge badge-teal">Open Source</span>
      <span class="badge badge-cyan">Free for 25 Users</span>
      <span class="badge badge-slate">SOC 2 + HIPAA + GDPR</span>
    </div>
  </div>

  <div class="footer">kavachiq.com</div>
</body>
</html>`;

async function generate() {
  console.log('Generating OG image (1200x630)...');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'networkidle0' });

  const screenshot = await page.screenshot({ type: 'jpeg', quality: 90 });
  writeFileSync(OUTPUT, screenshot);

  await browser.close();
  console.log(`  -> public/og-image.jpg (${(screenshot.length / 1024).toFixed(0)} KB)`);
}

generate().catch(err => {
  console.error('Failed:', err);
  process.exit(1);
});
