# KavachIQ — Design System Overhaul Plan

**Date: 2026-03-31 | Status: Planned**

---

## 1. Why

The current UI was built page-by-page without a unified design system. Each page has slightly different spacing, card styles, table patterns, and color usage. There's no mobile responsiveness — the sidebar is fixed-width, grids assume desktop, tables overflow on small screens.

For CISOs opening a demo link on their phone, investors checking the product between meetings, and MSPs doing quick health checks on mobile — the current experience breaks.

### Current Problems

| Problem | Impact |
|---------|--------|
| No unified component library | Every page looks slightly different |
| Fixed 224px sidebar, no mobile collapse | Unusable on phones |
| Hardcoded dark theme classes | Can't add light mode, no theme tokens |
| Tables overflow on mobile | Billing, MSP Dashboard unreadable |
| No touch-friendly targets | Buttons too small for fingers |
| Inconsistent spacing/typography | "Developer-built" feel |
| No design tokens | Colors scattered across 30+ files |

---

## 2. Solution: shadcn/ui + Tailwind CSS v4 Tokens + Mobile-First

### Why shadcn/ui

- **We already use Tailwind + React** — zero learning curve
- **Components copied into codebase** — full ownership, no dependency risk
- **Radix UI accessibility** — keyboard nav, ARIA compliance built in
- **Mobile responsive by default** — Sheet for mobile sidebar, responsive DataTable
- **Zero runtime JS overhead** — styles are Tailwind (purged at build)
- **Industry standard 2026** — Vercel, Linear, and most new SaaS use this
- **Theme tokens via CSS variables** — easy dark/light mode toggle

### What We Adopt

| shadcn Component | Replaces | Used Where |
|-----------------|----------|-----------|
| **Card** | Custom `bg-gray-800 rounded-xl` divs | Dashboard stats, tenant cards, billing |
| **Table** | Custom HTML tables | Billing, MSP overview, compliance, feature flags |
| **Dialog** | Custom modals | Compliance report, offboard workflow |
| **Sheet** | None (no mobile sidebar) | Mobile navigation drawer |
| **Tabs** | Custom tab buttons | Feature flags, compliance reports |
| **Badge** | Custom `px-1.5 py-0.5 rounded` spans | Status badges, health indicators |
| **Button** | Custom button classes | All buttons (primary, secondary, destructive) |
| **Input** | Custom input classes | Forms (branding, bulk onboard, login) |
| **Select** | Custom `<select>` | Month picker, workload selector |
| **Separator** | Custom border dividers | Section separators |
| **Tooltip** | Custom `title` attributes | Action buttons, health scores |
| **Progress** | Custom div-based bars | Health scores, backup progress |
| **Avatar** | Custom icon containers | Tenant logos, user avatars |
| **Command** | Existing CommandPalette | Upgrade to shadcn Command (Radix-based) |
| **Toast** | Existing Toast.tsx | Upgrade to shadcn Sonner integration |
| **DropdownMenu** | None | User menu, tenant actions |

---

## 3. Design Tokens

### Color System (CSS Variables)

```css
:root {
  /* Brand */
  --color-primary: #3b82f6;      /* blue-500 — interactive elements */
  --color-primary-hover: #2563eb; /* blue-600 */
  --color-primary-muted: #3b82f620; /* blue-500/10 */

  /* Semantic */
  --color-success: #22c55e;      /* green-500 */
  --color-warning: #f59e0b;      /* amber-500 */
  --color-danger: #ef4444;       /* red-500 */
  --color-info: #06b6d4;         /* cyan-500 */

  /* Surface (dark mode) */
  --color-bg: #0f172a;           /* slate-900 */
  --color-bg-card: #1e293b;      /* slate-800 */
  --color-bg-elevated: #334155;  /* slate-700 */
  --color-border: #334155;       /* slate-700 */
  --color-border-subtle: #1e293b40;

  /* Text */
  --color-text: #f8fafc;         /* slate-50 */
  --color-text-secondary: #94a3b8; /* slate-400 */
  --color-text-muted: #64748b;   /* slate-500 */
}

/* Light mode override */
[data-theme="light"] {
  --color-bg: #ffffff;
  --color-bg-card: #f8fafc;
  --color-bg-elevated: #f1f5f9;
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
}
```

### Typography Scale

```css
:root {
  --font-sans: 'Inter', -apple-system, system-ui, sans-serif;
  --text-xs: 0.75rem;    /* 12px — labels, badges */
  --text-sm: 0.875rem;   /* 14px — body, table cells */
  --text-base: 1rem;     /* 16px — paragraphs */
  --text-lg: 1.125rem;   /* 18px — section headers */
  --text-xl: 1.25rem;    /* 20px — page subtitles */
  --text-2xl: 1.5rem;    /* 24px — page titles */
  --text-3xl: 1.875rem;  /* 30px — hero */
}
```

### Spacing Scale

```css
/* Follow Tailwind default: 4px base unit */
/* Consistent padding: cards=p-4 (16px), sections=py-6 (24px), page=px-6 (24px) */
```

---

## 4. Mobile Responsive Strategy

### Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| `sm` | < 640px | Single column, sheet sidebar, stacked cards |
| `md` | 640-1024px | 2-column grids, collapsible sidebar |
| `lg` | > 1024px | Full layout, fixed sidebar |

### Mobile Navigation

```
Desktop: Fixed sidebar (w-56) + content area
Tablet:  Collapsible sidebar (toggle button in header)
Mobile:  Sheet sidebar (slides from left on hamburger tap) + full-width content
```

### Component Behavior

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Sidebar | Fixed, always visible | Sheet (hamburger menu) |
| Stat cards | 4-column grid | 2-column, then 1-column |
| Data tables | Full width with all columns | Horizontal scroll or card view |
| Dialogs | Centered modal | Bottom sheet (full width) |
| Charts | Side by side | Stacked |
| Forms | 2-column layout | Single column |

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1)
- Install shadcn/ui CLI + configure
- Set up CSS variable theme tokens
- Create base theme (dark + light mode)
- Migrate Layout.tsx to shadcn Sidebar + Sheet (mobile nav)
- Add theme toggle (dark/light)

### Phase 2: Core Components (Week 2)
- Migrate all Card patterns to shadcn Card
- Migrate all tables to shadcn DataTable
- Migrate all buttons to shadcn Button variants
- Migrate all inputs/selects to shadcn Form components
- Migrate all badges to shadcn Badge

### Phase 3: Page-by-Page Migration (Week 3)
- Dashboard (stat cards, workload cards, charts)
- MSP Dashboard (tenant cards, health badges)
- Billing Portal (table, month selector)
- Feature Flags (category cards, tier comparison table)
- Settings, Jobs, Audit pages

### Phase 4: Mobile Polish (Week 4)
- Test every page at 375px (iPhone SE)
- Fix overflow, touch targets, readable text
- Add swipe gestures for Sheet sidebar
- Test in Chrome DevTools mobile emulator
- Playwright mobile viewport tests

### Phase 5: Landing Page (Week 5)
- Responsive hero section
- Mobile pricing cards (horizontal scroll or stack)
- Mobile-friendly cyber recovery animation
- Touch-friendly CTAs

---

## 6. File Changes Summary

### New Files
- `frontend/src/components/ui/` — shadcn components (20+ files)
- `frontend/src/lib/utils.ts` — cn() utility for class merging
- `frontend/src/styles/tokens.css` — CSS variable theme tokens
- `frontend/src/components/ThemeToggle.tsx` — dark/light mode switch

### Major Modifications
- `frontend/src/components/Layout.tsx` — shadcn Sidebar + Sheet
- `frontend/src/pages/Dashboard.tsx` — shadcn Card + responsive grid
- `frontend/src/pages/MSPDashboard.tsx` — shadcn Card + responsive
- `frontend/src/pages/BillingPortal.tsx` — shadcn DataTable
- `frontend/src/pages/FeatureFlags.tsx` — shadcn Tabs + Table
- `frontend/src/components/OffboardWorkflow.tsx` — shadcn Dialog
- `frontend/src/components/ComplianceReport.tsx` — shadcn Dialog + Tabs
- `frontend/src/components/Toast.tsx` — replace with shadcn Sonner
- `frontend/src/pages/Landing.tsx` — responsive at all breakpoints
- All form pages (Login, MSPBranding, BulkOnboard) — shadcn Form + Input

---

## 7. Design References

| Reference | What to Study |
|-----------|--------------|
| [Linear](https://linear.app) | Strategic minimalism, whitespace, dark theme |
| [Vercel Dashboard](https://vercel.com/dashboard) | Data-first design, clean metrics |
| [shadcn/ui Dashboard](https://ui.shadcn.com/examples/dashboard) | Component patterns, chart layout |
| [Datadog](https://www.datadoghq.com) | Monitoring dashboard, real-time metrics |
| [SentinelOne](https://www.sentinelone.com) | Security dashboard, attack visualization |
| [SaaSFrame](https://www.saasframe.io/categories/dashboard) | 166 SaaS dashboard examples |
| [SaaSUI](https://www.saasui.design) | Real SaaS product screenshots |

---

## 8. Branch Strategy

```
main                          — Production (no design changes)
feature/msp-dashboard         — MSP features (no design changes)
feature/design-system         — Design system overhaul (shadcn + mobile)
```

Design system branch is independent from MSP. When both are ready, merge order:
1. Merge `feature/design-system` → `main` first
2. Rebase `feature/msp-dashboard` on new `main`
3. Merge MSP to `main`

This order avoids conflicts since the design system touches Layout, App.tsx, and component files that MSP also modified.

---

## 9. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Mobile usability (Lighthouse) | ~30 | 90+ |
| Component consistency | Ad-hoc per page | 1 design system |
| Theme switching | Dark only | Dark + Light toggle |
| Responsive breakpoints per page | 0-2 | 5+ (sm/md/lg/xl/2xl) |
| Touch target size | 20-30px | 44px minimum (WCAG) |
| Lighthouse Performance | ~75 | 90+ |
| Accessibility score | Unknown | 90+ (Radix built-in) |

---

## Sources

- [7 SaaS UI Design Trends 2026](https://www.saasui.design/blog/7-saas-ui-design-trends-2026)
- [shadcn/ui Dashboard Example](https://ui.shadcn.com/examples/dashboard)
- [shadcn/ui Best Practices 2026](https://medium.com/write-a-catalyst/shadcn-ui-best-practices-for-2026-444efd204f44)
- [Top 7 SaaS Design Trends B2B 2026](https://lollypop.design/blog/2025/april/saas-design-trends/)
- [B2B SaaS UX Design Patterns](https://www.onething.design/post/b2b-saas-ux-design)
- [166 SaaS Dashboard UI Examples](https://www.saasframe.io/categories/dashboard)
