/**
 * Generate per-page OG images (1200x630) for social sharing previews.
 *
 * Output: frontend/public/og-{slug}.jpg
 *
 * Each page gets a tailored image so LinkedIn/Twitter/Slack previews AND
 * AI agents reviewing the site from buyer personas (CEO, CDO, CTO) see a
 * clear visual signal of the page's specific angle.
 */

import { writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import puppeteer from 'puppeteer';

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Page definitions. `accent` is the color used for the highlighted word in the title.
 * `audience` is the target buyer persona used in the tagline line.
 */
const PAGES = [
  {
    slug: 'welcome',
    eyebrow: 'IDENTITY-FIRST CYBER RECOVERY · MICROSOFT 365',
    titleWhite: 'Recover Microsoft 365 safely,',
    titleAccent: 'starting with identity.',
    subtitle: 'Assess blast radius, restore Microsoft Entra first, recover critical users next, verify business recovery.',
    badges: ['Entra-First Recovery', 'Blast Radius Analysis', 'Guided Recovery Plans'],
  },
  {
    slug: 'about',
    eyebrow: 'IDENTITY COMES FIRST',
    titleWhite: 'Recovery starts with',
    titleAccent: 'who has admin access.',
    subtitle: 'Purpose-built for Microsoft 365 recovery. Identity first. Critical users next. Verified business recovery.',
    badges: ['12 Entra ID Object Types', 'NIST SP 800-184 Aligned', 'SOC 2 + HIPAA'],
  },
  {
    slug: 'tour',
    eyebrow: 'INTERACTIVE PRODUCT TOUR',
    titleWhite: 'Cyber recovery',
    titleAccent: 'in action.',
    subtitle: 'See how KavachIQ detects disruptive changes, assesses blast radius, and recovers Microsoft 365 in identity-first order.',
    badges: ['Protect → Detect → Recover', 'Blast Radius Diff', 'Recovery Verified'],
  },
  {
    slug: 'contact',
    eyebrow: 'REQUEST A DEMO',
    titleWhite: 'See KavachIQ in your',
    titleAccent: 'Microsoft 365 environment.',
    subtitle: 'Walk through a recovery scenario with a KavachIQ engineer. Demo, sales, and security paths available.',
    badges: ['Demo-Led', 'Procurement Ready', 'hello@kavachiq.com'],
  },
  {
    slug: 'overview',
    eyebrow: 'ONE-PAGE OVERVIEW',
    titleWhite: 'Identity-first cyber recovery for',
    titleAccent: 'Microsoft Entra and Microsoft 365.',
    subtitle: 'What KavachIQ is, who it is for, and why identity-first recovery matters. Forwardable after a call.',
    badges: ['Purpose-Built for M365', 'Entra-First', 'Enterprise Trust'],
  },
  {
    slug: 'scenarios',
    eyebrow: 'ILLUSTRATIVE RECOVERY SCENARIOS',
    titleWhite: 'Recovery scenarios for',
    titleAccent: 'Microsoft 365.',
    subtitle: 'Operator-grade walkthroughs of identity-first cyber recovery for common Microsoft 365 incidents.',
    badges: ['Identity Compromise', 'Destructive Deletion', 'Bulk Mailbox Loss'],
  },
  {
    slug: 'scenario-global-admin',
    eyebrow: 'RECOVERY SCENARIO',
    titleWhite: 'Compromised Global Admin',
    titleAccent: 'in Microsoft 365.',
    subtitle: 'Identity-first recovery applied end-to-end: contain blast radius, restore Entra controls, recover critical users, verify business recovery.',
    badges: ['Protect → Verify', 'Entra-First Restore', 'Evidence-Based Sign-Off'],
  },
  {
    slug: 'scenario-destructive-deletion',
    eyebrow: 'RECOVERY SCENARIO',
    titleWhite: 'Destructive deletion across',
    titleAccent: 'SharePoint and OneDrive.',
    subtitle: 'Identify affected users, sites, libraries, and files. Restore the right content in the right order. Verify recovery with evidence.',
    badges: ['Blast Radius Across Sites', 'Prioritized Restore', 'Verified Recovery'],
  },
  {
    slug: 'scenario-bulk-mailbox-deletion',
    eyebrow: 'RECOVERY SCENARIO',
    titleWhite: 'Bulk mailbox deletion and',
    titleAccent: 'retention drift in Microsoft 365.',
    subtitle: 'Recover mailboxes past the native window, restore the right retention posture, and produce evidence for compliance review.',
    badges: ['Past Native Windows', 'Retention Posture Verified', 'Compliance Evidence'],
  },
  {
    slug: 'security',
    eyebrow: 'ENTERPRISE TRUST',
    titleWhite: 'Enterprise security for',
    titleAccent: 'Microsoft 365 cyber recovery.',
    subtitle: 'Tenant-scoped access, encryption, immutability, auditability, and compliance-mapped controls from day one.',
    badges: ['AES-256-GCM', 'Per-Tenant Keys', 'WORM · Audit Trail'],
  },
];

function html({ eyebrow, titleWhite, titleAccent, subtitle, badges }) {
  return `<!DOCTYPE html>
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

  body::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(45,212,191,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(45,212,191,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  .glow {
    position: absolute;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(45,212,191,0.12) 0%, transparent 70%);
    top: -100px; right: -100px;
  }
  .glow-2 {
    position: absolute;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%);
    bottom: -80px; left: -80px;
  }

  .content {
    position: relative; z-index: 1;
    text-align: center;
    padding: 0 70px;
    max-width: 1100px;
  }

  .logo-row {
    display: flex; align-items: center; justify-content: center;
    gap: 14px; margin-bottom: 20px;
  }
  .shield { width: 44px; height: 44px; }
  .logo-text {
    font-size: 28px; font-weight: 700;
    color: #e2e8f0; letter-spacing: -0.5px;
  }

  .eyebrow {
    display: inline-block;
    font-size: 13px; font-weight: 700;
    letter-spacing: 2px;
    color: #2dd4bf;
    padding: 6px 16px;
    background: rgba(45,212,191,0.10);
    border: 1px solid rgba(45,212,191,0.25);
    border-radius: 999px;
    margin-bottom: 24px;
  }

  h1 {
    font-size: 56px; font-weight: 800;
    line-height: 1.1;
    letter-spacing: -1.5px;
    margin-bottom: 22px;
  }
  h1 .white { color: #f1f5f9; display: block; }
  h1 .accent { color: #2dd4bf; display: block; }

  .subtitle {
    font-size: 22px;
    color: #94a3b8;
    line-height: 1.45;
    max-width: 900px;
    margin: 0 auto 30px;
    font-weight: 400;
  }

  .badges {
    display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
  }
  .badge {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px; font-weight: 600;
    letter-spacing: 0.3px;
    background: rgba(45,212,191,0.12);
    color: #5eead4;
    border: 1px solid rgba(45,212,191,0.22);
  }

  .footer {
    position: absolute;
    bottom: 24px; left: 0; right: 0;
    text-align: center;
    font-size: 14px; color: #475569;
    letter-spacing: 0.4px;
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

    <div class="eyebrow">${eyebrow}</div>

    <h1>
      <span class="white">${titleWhite}</span>
      <span class="accent">${titleAccent}</span>
    </h1>

    <p class="subtitle">${subtitle}</p>

    <div class="badges">
      ${badges.map((b) => `<span class="badge">${b}</span>`).join('')}
    </div>
  </div>

  <div class="footer">kavachiq.com</div>
</body>
</html>`;
}

async function generate() {
  console.log('\nGenerating per-page OG images (1200x630, ~70KB each)...\n');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });

  for (const def of PAGES) {
    await page.setContent(html(def), { waitUntil: 'domcontentloaded' });
    const screenshot = await page.screenshot({ type: 'jpeg', quality: 90 });
    const out = join(__dirname, '..', 'public', `og-${def.slug}.jpg`);
    writeFileSync(out, screenshot);
    console.log(`  public/og-${def.slug}.jpg (${(screenshot.length / 1024).toFixed(0)} KB)`);
  }

  await browser.close();
  console.log(`\nGenerated ${PAGES.length} OG images.\n`);
}

generate().catch((err) => {
  console.error('Failed:', err);
  process.exit(1);
});
