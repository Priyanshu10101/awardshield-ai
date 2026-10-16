# AwardShield UI – full build (Angular 22)

This file contains **every source file** of `awardshield/ui/`. Recreate each file at the path shown, byte for byte, then build.
Folder: `awardshield/ui/` (sibling of `api/`, `agent/`, `engine/`, `data/`).

## What it is
- Angular 22, standalone components, **zoneless** (`provideZonelessChangeDetection`), hash routing (`#/case/IN-CRUT-EBUS`), lazy routes, view transitions, `anchorScrolling`.
- Charts: ECharts 6 via ngx-echarts (lazy core, tree-shaken in `shared/echarts-setup.ts`).
- Theme: light "Evidence Desk" (paper/ink, Instrument Serif + Geist) with one dark engine-console band. Tokens: `src/styles.scss`, contract: `DESIGN.md`.
- Talks only to the FastAPI backend at relative `api/...` (see NEW_BACKEND_CHANGES.md).

| Route | Component | Purpose |
|---|---|---|
| `#/` | `pages/landing.ts` (+ `hero-doc.ts`, `acts.ts`) | first impression: plain-language 3-step hero (price on paper → TrueCost 12-yr cost → RedSeal catch), 3-act story chart, two parts, verdict, Google stack |
| `#/case/:id` | `pages/decision.ts` | committee decision: verdict, conditional outcomes, links deeper |
| `#/case/:id/truecost` | `pages/truecost.ts` | TrueCost part: bidder evidence quotes, official indices (url/sha256), buyer questions |
| `#/case/:id/engine` | `pages/engine.ts` | deterministic engine: escalation curves, live what-if sliders (`POST /evaluate`) |
| `#/case/:id/redseal` | `pages/redseal.ts` | RedSeal part: challenge ledger, flip thresholds, sensitivity |
| `#/case/:id/run` | `pages/run.ts` | time-coded replay of recorded ADK agent runs |

## Build & run (laptop)
```bash
# 1. backend data must exist (see NEW_BACKEND_CHANGES.md: generate bids -> truecost -> redseal)
cd awardshield/ui
npm install
npx ng build                # -> ui/dist/awardshield-ui/browser
cd ..
uvicorn api.app:app --port 8900   # serves API + built UI at http://127.0.0.1:8900/
# dev mode with hot reload instead (proxies /api -> 8900):
cd ui && npx ng serve       # http://localhost:4200
```

Notes
- `zone.js` is listed in package.json but NOT imported – the app is zoneless. Do not add `provideZoneChangeDetection`.
- If `ng build` complains about fonts, run `npm install` again (fonts come from `@fontsource*` packages).
- The engine page reads each bidder's parameter name from `engine` -> `rates[Supplier].param` (e.g. `unit_rate_base`, `unit_rate_main`, `urbandrive`, `unit_rate_gcc`), so it adapts if TrueCost names them differently.
- Verified: `ng build` OK; Playwright at 1440/768/375 px – no horizontal overflow, no console errors on all 6 pages; slider -> `/evaluate` flips winner; run replay plays.
---

## `ui/package.json`
```json
{
  "name": "awardshield-ui",
  "version": "0.0.0",
  "scripts": {
    "ng": "ng",
    "start": "ng serve",
    "build": "ng build",
    "watch": "ng build --watch --configuration development"
  },
  "private": true,
  "packageManager": "npm@11.19.0",
  "dependencies": {
    "@angular/common": "^22.2.0",
    "@angular/compiler": "^22.2.0",
    "@angular/core": "^22.2.0",
    "@angular/platform-browser": "^22.2.0",
    "@angular/router": "^22.2.2",
    "echarts": "^6.1.0",
    "ngx-echarts": "^22.0.0",
    "rxjs": "~7.8.0",
    "tslib": "^2.3.0",
    "zone.js": "^0.16.3",
    "@fontsource-variable/instrument-sans": "^5.3.0",
    "@fontsource/instrument-serif": "^5.3.0",
    "@fontsource-variable/geist": "^5.3.0",
    "@fontsource-variable/geist-mono": "^5.3.0"
  },
  "devDependencies": {
    "@angular/build": "^22.2.2",
    "@angular/cli": "^22.2.2",
    "@angular/compiler-cli": "^22.2.0",
    "prettier": "^3.8.1",
    "typescript": "~6.0.2"
  }
}
```

## `ui/angular.json`
```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "cli": { "packageManager": "npm", "analytics": false },
  "newProjectRoot": "projects",
  "projects": {
    "awardshield-ui": {
      "projectType": "application",
      "schematics": { "@schematics/angular:component": { "style": "scss" } },
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular/build:application",
          "options": {
            "browser": "src/main.ts",
            "tsConfig": "tsconfig.app.json",
            "inlineStyleLanguage": "scss",
            "assets": [{ "glob": "**/*", "input": "public" }],
            "styles": [
              "node_modules/@fontsource-variable/geist/index.css",
              "node_modules/@fontsource-variable/geist-mono/index.css",
              "node_modules/@fontsource/instrument-serif/400.css",
              "node_modules/@fontsource/instrument-serif/400-italic.css",
              "src/styles.scss"
            ],
            "outputPath": "dist/awardshield-ui"
          },
          "configurations": {
            "production": {
              "budgets": [
                { "type": "initial", "maximumWarning": "700kB", "maximumError": "1.5MB" },
                { "type": "anyComponentStyle", "maximumWarning": "12kB", "maximumError": "24kB" }
              ],
              "outputHashing": "all"
            },
            "development": { "optimization": false, "extractLicenses": false, "sourceMap": true }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular/build:dev-server",
          "options": { "proxyConfig": "proxy.conf.json" },
          "configurations": {
            "production": { "buildTarget": "awardshield-ui:build:production" },
            "development": { "buildTarget": "awardshield-ui:build:development" }
          },
          "defaultConfiguration": "development"
        }
      }
    }
  }
}
```

## `ui/tsconfig.json`
```json
{
  "compileOnSave": false,
  "compilerOptions": {
    "strict": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "experimentalDecorators": true,
    "importHelpers": true,
    "target": "ES2022",
    "module": "preserve"
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  },
  "files": [],
  "references": [{ "path": "./tsconfig.app.json" }]
}
```

## `ui/tsconfig.app.json`
```json
/* To learn more about Typescript configuration file: https://www.typescriptlang.org/docs/handbook/tsconfig-json.html. */
/* To learn more about Angular compiler options: https://angular.dev/reference/configs/angular-compiler-options. */
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "types": []
  },
  "include": [
    "src/**/*.ts"
  ],
  "exclude": [
    "src/**/*.spec.ts"
  ]
}
```

## `ui/proxy.conf.json`
```json
{ "/api": { "target": "http://127.0.0.1:8900", "secure": false, "changeOrigin": true } }
```

## `ui/public/favicon.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#C2361F"/><circle cx="32" cy="32" r="21" fill="none" stroke="#FDF0EC" stroke-width="2" stroke-dasharray="3 3"/><path d="M22 33l7 7 13-15" fill="none" stroke="#FFFDF8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>
```

## `ui/src/index.html`
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AwardShield – every award, proven</title>
  <base href="./">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AwardShield: TrueCost reads every bid and computes the true lifetime cost; RedSeal tries to break the award and proves what it finds.">
  <meta name="theme-color" content="#F4F1EA">
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
</head>
<body>
  <app-root></app-root>
</body>
</html>
```

## `ui/src/main.ts`
```ts
import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config';

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
```

## `ui/src/styles.scss`
```scss
/* AwardShield "Evidence Desk" - tokens + primitives. Contract: DESIGN.md */

:root {
  --paper: #f4f1ea;
  --paper-2: #ece7dc;
  --sheet: #fffff8;
  --ink: #15171c;
  --ink-2: #3d424d;
  --ink-3: #6b7080;
  --rule: #ddd6c8;
  --rule-2: #c9c0ae;
  --tc: #2447d8;
  --tc-50: #eef2ff;
  --tc-100: #dce4ff;
  --tc-700: #1a34a6;
  --rs: #c2361f;
  --rs-50: #fdf0ec;
  --rs-100: #f8dad2;
  --rs-700: #8e2414;
  --h1: #ffe58a;
  --ok: #1e7a4f;
  --ok-50: #e9f5ee;
  --warn: #b26a00;
  --warn-50: #fff4e0;
  --console: #0e1013;
  --console-2: #171a1f;
  --console-line: rgba(255, 255, 255, 0.09);
  --console-ink: #f2f0ea;
  --console-ink-2: #9da3ae;
  --g-blue: #4285f4;
  --g-red: #ea4335;
  --g-yellow: #fbbc04;
  --g-green: #34a853;
  --bid-gm: #2f7d5b;
  --bid-ml: #2447d8;
  --bid-ud: #8a6f3e;

  --serif: 'Instrument Serif', 'Times New Roman', serif;
  --sans: 'Geist Variable', system-ui, -apple-system, sans-serif;
  --mono: 'Geist Mono Variable', ui-monospace, 'SF Mono', Menlo, monospace;

  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px; --s6: 24px; --s8: 32px;
  --s10: 40px;
  --s12: 48px; --s16: 64px; --s20: 80px; --s24: 96px; --s32: 128px;
  --r1: 6px; --r2: 10px; --r3: 16px; --r4: 24px;
  --wrap: 1200px;

  --shadow-1: 0 1px 2px rgba(40, 30, 10, 0.06), 0 1px 1px rgba(40, 30, 10, 0.04);
  --shadow-2: 0 6px 18px -6px rgba(40, 30, 10, 0.14), 0 2px 4px rgba(40, 30, 10, 0.05);
  --shadow-doc: 0 30px 60px -20px rgba(40, 30, 10, 0.25), 0 12px 24px -12px rgba(40, 30, 10, 0.12);

  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-seal: cubic-bezier(0.34, 1.56, 0.64, 1);
  --t-micro: 140ms; --t-std: 260ms; --t-emph: 620ms;
  color-scheme: light;
}

*, *:before, *:after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink-2);
  font: 400 15.5px/1.6 var(--sans);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
/* paper grain: one fixed overlay, never on scrolling content */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 100;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

h1, h2, h3, h4 { color: var(--ink); margin: 0; }
p { margin: 0; }
a { color: var(--tc); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 3px; }
button { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--tc); outline-offset: 2px; border-radius: 6px; }
::selection { background: var(--h1); color: var(--ink); }

/* --------- type --------- */
.serif { font-family: var(--serif); font-weight: 400; }
.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.tnum { font-variant-numeric: tabular-nums; }
.display { font-family: var(--serif); font-weight: 400; font-size: clamp(32px, 3.6vw, 52px); line-height: 1.05; letter-spacing: -0.015em; color: var(--ink); }
.display em { font-style: italic; }
.h1 { font: 600 28px/1.2 var(--sans); letter-spacing: -0.02em; color: var(--ink); }
.h2 { font: 600 20px/1.3 var(--sans); letter-spacing: -0.01em; color: var(--ink); }
.lead { font-size: 19px; line-height: 1.55; letter-spacing: -0.005em; color: var(--ink-2); }
.small { font-size: 13.5px; line-height: 1.5; }
.muted { color: var(--ink-3); }
.overline { font: 600 11.5px/1.3 var(--sans); letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-3); }
.fig { font: 500 15px/1.4 var(--mono); font-variant-numeric: tabular-nums; color: var(--ink); }
.bigfig { font: 500 clamp(30px, 3.2vw, 44px)/1 var(--mono); letter-spacing: -0.03em; font-variant-numeric: tabular-nums; color: var(--ink); }

/* --------- layout --------- */
.wrap { width: 100%; max-width: var(--wrap); margin: 0 auto; padding: 0 var(--s6); }
.section { padding: var(--s24) 0; }
.band { background: var(--paper-2); }
.row { display: flex; align-items: center; gap: var(--s3); }
.spacer { flex: 1; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s6); }
.grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s6); }
@media (max-width: 900px) {
  .section { padding: var(--s16) 0; }
  .grid-2, .grid-3 { grid-template-columns: minmax(0, 1fr); }
  .wrap { padding: 0 var(--s4); }
}

/* --------- buttons --------- */
.btn {
  display: inline-flex; align-items: center; gap: var(--s3);
  padding: 8px 8px 8px 20px; border-radius: 999px; border: 1px solid var(--ink);
  background: var(--ink); color: var(--paper); font: 500 15px/1 var(--sans);
  cursor: pointer;
  transition: transform var(--t-micro) var(--ease), background var(--t-micro) var(--ease), box-shadow var(--t-std) var(--ease);
  text-decoration: none !important; white-space: nowrap;
}
.btn .ico { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; background: rgba(255, 255, 255, 0.12); transition: transform var(--t-std) var(--ease); }
.btn:hover { box-shadow: var(--shadow-2); }
.btn:hover .ico { transform: translateX(2px); }
.btn:active { transform: scale(0.98); }
.btn-ghost { background: transparent; color: var(--ink); border-color: var(--rule-2); }
.btn-ghost .ico { background: var(--paper-2); }
.btn-tc { background: var(--tc); border-color: var(--tc); color: #fff; }
.btn-rs { background: var(--rs); border-color: var(--rs); color: #fff; }
.btn-sm { padding: 6px 14px; font-size: 13.5px; }
.btn:disabled { opacity: 0.45; pointer-events: none; }

/* --------- surfaces --------- */
.card { background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--r3); box-shadow: var(--shadow-1); }
.card-b { padding: var(--s6); }
.card.hoverable { transition: transform var(--t-std) var(--ease), box-shadow var(--t-std) var(--ease); }
.card.hoverable:hover { transform: translateY(-2px); box-shadow: var(--shadow-2); }
.bezel { background: var(--paper-2); border: 1px solid var(--rule); border-radius: var(--r4); padding: 6px; }
.bezel > .core { background: var(--sheet); border-radius: calc(var(--r4) - 6px); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--shadow-1); }
.console { background: var(--console); color: var(--console-ink-2); }
.console .h1, .console .h2, .console .display { color: var(--console-ink); }

/* --------- pills / chips --------- */
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font: 500 12.5px/1.4 var(--sans); border: 1px solid var(--rule-2); color: var(--ink-2); background: var(--sheet); white-space: nowrap; }
.pill.tc { background: var(--tc-50); border-color: var(--tc-100); color: var(--tc-700); }
.pill.rs { background: var(--rs-50); border-color: var(--rs-100); color: var(--rs-700); }
.pill.ok { background: var(--ok-50); border-color: #cfe6d9; color: var(--ok); }
.pill.warn { background: var(--warn-50); border-color: #f2d9a6; color: var(--warn); }
.pill.code { background: var(--console); border-color: var(--console); color: var(--console-ink); font-family: var(--mono); font-size: 11.5px; }
.pill.mute { color: var(--ink-3); text-decoration: line-through; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; display: inline-block; }

.quote { background: linear-gradient(transparent 12%, var(--h1) 12%, var(--h1) 88%, transparent 88%); color: var(--ink); font-family: var(--mono); font-size: 13px; padding: 0 3px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.src { font: 500 11px/1 var(--mono); color: var(--ink-3); letter-spacing: 0.02em; }

/* --------- tables --------- */
.dtable { width: 100%; border-collapse: collapse; font-size: 14px; }
.dtable th { text-align: left; font: 600 11.5px/1.3 var(--sans); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-3); padding: 10px 12px; border-bottom: 1px solid var(--rule-2); background: var(--paper-2); }
.dtable td { padding: 12px; border-bottom: 1px solid var(--rule); vertical-align: top; color: var(--ink-2); }
.dtable td.num, .dtable th.num { white-space: nowrap; text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }
.dtable tr:last-child td { border-bottom: 0; }

/* --------- tabs (segmented) --------- */
.seg { display: inline-flex; padding: 4px; gap: 2px; background: var(--paper-2); border: 1px solid var(--rule); border-radius: 999px; position: relative; }
.seg button { border: 0; background: transparent; padding: 7px 16px; border-radius: 999px; cursor: pointer; font: 500 14px/1 var(--sans); color: var(--ink-3); position: relative; z-index: 1; transition: color var(--t-std) var(--ease); }
.seg button.on { color: var(--ink); background: var(--sheet); box-shadow: var(--shadow-1); }

/* --------- motion --------- */
.reveal { opacity: 0; transform: translateY(16px); transition: opacity var(--t-emph) var(--ease-out), transform var(--t-emph) var(--ease-out); }
.reveal.in { opacity: 1; transform: none; }
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.rise { animation: rise var(--t-emph) var(--ease-out) both; animation-delay: calc(var(--i, 0) * 70ms); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.live { animation: pulse 1.6s var(--ease) infinite; }

@media (prefers-reduced-motion: reduce) {
  *, *:before, *:after { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; transition-duration: 0.001ms !important; scroll-behavior: auto !important; }
  .reveal { opacity: 1; transform: none; }
}
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
```

## `ui/src/app/app.config.ts`
```ts
import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, withComponentInputBinding, withHashLocation, withInMemoryScrolling, withViewTransitions } from '@angular/router';
import { provideEchartsCore } from 'ngx-echarts';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding(), withHashLocation(), withInMemoryScrolling({ scrollPositionRestoration: 'top', anchorScrolling: 'enabled' }), withViewTransitions({ skipInitialTransition: true })),
    provideHttpClient(),
    provideEchartsCore({ echarts: () => import('./shared/echarts-setup') }),
  ],
};
```

## `ui/src/app/app.routes.ts`
```ts
import { Routes } from '@angular/router';

const t = (p: string) => `${p} – AwardShield`;
export const routes: Routes = [
  { path: '', title: 'AwardShield – every award, proven', loadComponent: () => import('./pages/landing').then((m) => m.Landing) },
  { path: 'case/:id', title: t('Decision'), loadComponent: () => import('./pages/decision').then((m) => m.Decision) },
  { path: 'case/:id/truecost', title: t('TrueCost'), loadComponent: () => import('./pages/truecost').then((m) => m.TrueCostPage) },
  { path: 'case/:id/engine', title: t('Engine'), loadComponent: () => import('./pages/engine').then((m) => m.EnginePage) },
  { path: 'case/:id/redseal', title: t('RedSeal'), loadComponent: () => import('./pages/redseal').then((m) => m.RedSealPage) },
  { path: 'case/:id/run', title: t('Agent run'), loadComponent: () => import('./pages/run').then((m) => m.RunPage) },
  { path: '**', redirectTo: '' },
];
```

## `ui/src/app/app.ts`
```ts
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Icon } from './shared/icon';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<a class="skip" href="#main">Skip to content</a>
<header class="topbar" role="banner">
  <nav class="bar" aria-label="Main">
    <a routerLink="/" class="brand" aria-label="AwardShield home">
      <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28" fill="#C2361F"/><circle cx="32" cy="32" r="21" fill="none" stroke="#FDF0EC" stroke-width="2" stroke-dasharray="3 3"/><path d="M22 33l7 7 13-15" fill="none" stroke="#FFFDF8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="word">Award<b>Shield</b></span>
    </a>
    <div class="links" [class.open]="menu()">
      <a routerLink="/" [routerLinkActiveOptions]="{exact:true}" routerLinkActive="on" (click)="menu.set(false)">Home</a>
      <a routerLink="/case/IN-CRUT-EBUS" [routerLinkActiveOptions]="{exact:true}" routerLinkActive="on" (click)="menu.set(false)">Decision</a>
      <a routerLink="/case/IN-CRUT-EBUS/truecost" routerLinkActive="on" (click)="menu.set(false)"><i class="d tc"></i>TrueCost</a>
      <a routerLink="/case/IN-CRUT-EBUS/engine" routerLinkActive="on" (click)="menu.set(false)"><i class="d ink"></i>Engine</a>
      <a routerLink="/case/IN-CRUT-EBUS/redseal" routerLinkActive="on" (click)="menu.set(false)"><i class="d rs"></i>RedSeal</a>
      <a routerLink="/case/IN-CRUT-EBUS/run" routerLinkActive="on" (click)="menu.set(false)">Agent run</a>
    </div>
    <a routerLink="/case/IN-CRUT-EBUS" class="btn btn-sm cta">Open the audit</a>
    <button class="menu" type="button" [attr.aria-expanded]="menu()" (click)="menu.set(!menu())"><app-icon name="menu" [size]="20"/></button>
  </nav>
</header>
<main id="main"><router-outlet/></main>
<footer class="foot">
  <div class="wrap row">
    <span class="small muted">AwardShield · TrueCost + RedSeal · built on Gemini and Google ADK</span>
    <span class="spacer"></span>
    <span class="small muted">The AI builds the inputs. Code decides.</span>
  </div>
</footer>
`,
styles: [`
  .skip { position: absolute; left: -9999px; } .skip:focus { left: 16px; top: 12px; z-index: 200; background: var(--ink); color: var(--paper); padding: 8px 14px; border-radius: 8px; }
  .topbar { position: sticky; top: 0; z-index: 50; padding: 14px var(--s4) 0; pointer-events: none; }
  .bar { pointer-events: auto; max-width: var(--wrap); margin: 0 auto; display: flex; align-items: center; gap: var(--s4); padding: 8px 8px 8px 18px; border-radius: 999px; background: rgba(255,253,248,.86); border: 1px solid var(--rule); box-shadow: var(--shadow-2); backdrop-filter: blur(14px) saturate(1.2); -webkit-backdrop-filter: blur(14px) saturate(1.2); }
  .brand { display: flex; align-items: center; gap: 10px; color: var(--ink); text-decoration: none !important; }
  .word { font: 500 17px/1 var(--sans); letter-spacing: -0.02em; } .word b { font-weight: 650; }
  .links { display: flex; gap: 2px; margin-left: var(--s4); flex: 1; }
  .links a { color: var(--ink-3); padding: 7px 12px; border-radius: 999px; font: 500 14px/1 var(--sans); display: inline-flex; align-items: center; gap: 7px; text-decoration: none !important; transition: color var(--t-micro) var(--ease), background var(--t-micro) var(--ease); }
  .links a:hover { color: var(--ink); background: var(--paper-2); }
  .links a.on { color: var(--ink); background: var(--paper-2); }
  .d { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
  .tc { background: var(--tc); } .rs { background: var(--rs); } .ink { background: var(--ink); }
  .menu { display: none; border: 0; background: transparent; cursor: pointer; padding: 8px; border-radius: 999px; color: var(--ink); }
  .foot { border-top: 1px solid var(--rule); padding: var(--s8) 0; margin-top: var(--s16); }
  @media (max-width: 900px) {
    .menu { display: inline-flex; } .cta { display: none; }
    .links { display: none; position: absolute; top: 64px; left: var(--s4); right: var(--s4); flex-direction: column; background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--r3); padding: var(--s2); box-shadow: var(--shadow-2); margin: 0; }
    .links.open { display: flex; } .links a { padding: 12px 14px; }
    .bar { justify-content: space-between; }
  }
`] })
export class App {
  protected readonly menu = signal(false);
}
```

## `ui/src/app/core/api.ts`
```ts
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

export type Ranking = [string, number][];
export interface Bidder {
  name: string; rate: number; rate_param: string; amount_in_words: string;
  sticker_cr: number; lifetime_cr: number; year_one_cr: number; factor_end: number;
  fixed: number | null; terms: [string, number][];
}
export interface CaseOverview {
  id: string; title: string; buyer: string; country: string; currency: string;
  start: string; months: number; base_year: number;
  discount: { annual: number; monthly: number; method: string };
  volume: { id: string; label: string; build: string; components: [string, number, string][][] };
  bidders: Bidder[];
  acts: {
    sticker: { ranking: Ranking; winner: string };
    lifetime: { ranking: Ranking; winner: string; margin_cr: number };
    after: { ranking: Ranking; winner: string; challenge: string; change: string } | null;
    year_one_winner: string;
  };
  verdict: {
    status: 'OVERTURNED' | 'UNDERSTATED' | 'CERTIFIED_ROBUST'; contested: boolean;
    original_winner: string;
    final_winner: string; summary: string; fragile: boolean;
    narrative: { headline: string; findings: string[]; recommendation: string } |
    null;
  } | null;
}
export interface Evidence { document: string; page?: string; quote: string }
export interface Challenge {
  challenge_id: string; agent: string; kind: string; target: string; supplier:
  string;
  original_value: string; corrected_value: string; status: 'verified' |
  'contested' | 'rejected' | 'finding';
  checks: string[]; evidence: Evidence[]; evidence_against: Evidence[]; reasoning:
  string;
  overrides: Record<string, unknown>; rerun: { label: string; ranking: Ranking;
  winner: string; margin_cr: number } | null;
  effect: string;
}
export interface ProofPack {
  rfq_id: string; status: string; contested: boolean; original_winner: string;
  final_winner: string;
  baseline: { ranking: Ranking; winner: string; margin_cr: number };
  challenges: Challenge[];
  flip_thresholds: { supplier: string; param: string; current: number; threshold:
  number; change_pct: number; against: string; plausible: boolean }[];
  sensitivity: { driver: string; low_label: string; high_label: string; winner_low:
  string; winner_high: string; swing_cr: number; flips: boolean }[];
  fragile: boolean; summary: string;
  narrative: { headline: string; findings: string[]; recommendation: string } |
  null;
}
export interface RunEvent { t: number; agent: string; kind: 'call' | 'result' |
  'done'; name: string; detail: string; tokens?: number }
export interface RunRecord { run: string; rfq_id: string; started_at: string;
  duration_s: number; events: RunEvent[]; bidders?: string[]; verdict?: string }
export interface WhatIf {
  award: { ranking: Ranking; winner: string; runner_up: string; margin_cr: number;
  margin_pct: number };
  sticker: { ranking: Ranking; winner: string };
  yearly: Record<string, Record<string, number>>;
  factors: Record<string, Record<string, number>>;
  discount: { annual: number }; months: number; start: string;
}

@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private cache = new Map<string, Observable<unknown>>();

  private get<T>(url: string): Observable<T> {
    if (!this.cache.has(url)) this.cache.set(url, this.http.get<T>(url).pipe(
    shareReplay(1)));
    return this.cache.get(url) as Observable<T>;
  }
  case(id: string) { return this.get<CaseOverview>(`api/cases/${encodeURIComponent(id)}`); }
  truecost(id: string) { return this.get<any>(`api/cases/${encodeURIComponent(id)}/truecost`); }
  engine(id: string) { return this.get<any>(`api/cases/${encodeURIComponent(id)}/engine`); }
  redseal(id: string) { return this.get<ProofPack>(`api/cases/${encodeURIComponent(id)}/redseal`); }
  runs(id: string) { return this.get<Record<string, RunRecord>>(`api/cases/${encodeURIComponent(id)}/runs`); }
  evaluate(id: string, overrides: Record<string, unknown>) {
    return this.http.post<WhatIf>(`api/cases/${encodeURIComponent(id)}/evaluate`, {
    overrides });
  }
  docUrl(id: string, name: string) { return `api/cases/${encodeURIComponent(id)}/documents/${encodeURIComponent(name)}`; }
}

export const CASE_ID = 'IN-CRUT-EBUS';
export const BIDDER_COLOR: Record<string, string> = { GreenMetro: '#2F7D5B',
MetroLink: '#2447D8', UrbanDrive: '#8A6F3E' };
export const cr = (v: number, d = 2) => `₹${v.toLocaleString('en-IN', {
minimumFractionDigits: d, maximumFractionDigits: d })} cr`;
export const inr = (v: number) => `₹${v.toFixed(2)}`;
```

## `ui/src/app/shared/echarts-setup.ts`
```ts
/** Tree-shaken ECharts build: only what AwardShield uses (lazy chunk). */
import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent,
TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent,
MarkLineComponent, MarkPointComponent, CanvasRenderer]);

export * from 'echarts/core';
export default echarts;
```

## `ui/src/app/shared/chart.ts`
```ts
import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, input,
signal, untracked } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { ECharts, EChartsCoreOption } from 'echarts/core';

/**
 * One ECharts canvas. The first non-empty option initialises the chart; later
 * options are merged with
 * `replaceMerge: ['series']` so same-named series morph (bars grow, lines redraw)
 * instead of being rebuilt.
 */
@Component({
  selector: 'app-chart',
  imports: [NgxEchartsDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div echarts class="ec" [options]="initial()" [style.height]="height() + 'px'"
  [initOpts]="{ renderer: 'canvas' }" [autoResize]="true" (chartInit)="onInit($event)"></div>`,
  styles: [':host{display:block;min-width:0} .ec{width:100%;min-height:120px}']
})
export class Chart {
  readonly options = input.required<EChartsCoreOption>();
  /** px; 0 = fill the host's height */
  readonly height = input<number>(300);
  protected readonly initial = signal<EChartsCoreOption>({});
  private chart: ECharts | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => (this.chart = null));
    effect(() => {
      const o = this.options();
      if (!o || !Object.keys(o).length) return;
      untracked(() => {
        const opt = withIds(o);
        // until the canvas exists, the directive's [options] carries the latest;
        // afterwards merge so series morph
        if (!this.chart) this.initial.set(opt);
        else if (this.chart && !this.chart.isDisposed()) this.chart.setOption(opt,
        { replaceMerge: ['series'] });
      });
    });
  }

  protected onInit(c: ECharts): void {
    this.chart = c;
  }
}

/** Give every series a stable id (name|stack|index) so replaceMerge maps it onto
the existing one and morphs. */
function withIds(o: EChartsCoreOption): EChartsCoreOption {
  const ss = (o as { series?: unknown }).series;
  if (!Array.isArray(ss)) return o;
  const series = ss.map((x: unknown, i: number) => {
    const s = x as Record<string, unknown>;
    return s['id'] !== undefined ? s : { ...s, id: `${String(s['name']) ?? ''}|${String(s['stack']) ?? ''}|${i}` };
  });
  return { ...o, series };
}

/** Evidence-desk chart styling (DESIGN.md section 2 + 3). */
export const INK = { ink: '#15171C', ink2: '#3D424D', ink3: '#6B7080', rule:
'#DDD6C8', sheet: '#FFFFF8', tc: '#2447D8', rs: '#C2361F' };
export function chartBase(): Record<string, unknown> {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Geist Variable, system-ui, sans-serif', color: INK.
    ink2, fontSize: 12 },
    animationDuration: 700, animationEasing: 'cubicOut', animationDurationUpdate:
    650, animationEasingUpdate: 'cubicInOut',
    tooltip: {
      backgroundColor: INK.sheet, borderColor: INK.rule, borderWidth: 1, padding:
      [10, 14],
      textStyle: { color: INK.ink, fontSize: 12 },
      extraCssText: 'box-shadow:0 12px 30px -10px rgba(40,30,10,.25); border-radius:10px;',
    },
  };
}
export function axis(): Record<string, unknown> {
  return {
    axisLine: { lineStyle: { color: INK.rule } }, axisTick: { show: false },
    axisLabel: { color: INK.ink3, fontSize: 11, fontFamily: 'Geist Mono Variable,
    monospace' },
    splitLine: { lineStyle: { color: INK.rule, type: [3, 4] } },
  };
}
```

## `ui/src/app/shared/icon.ts`
```ts
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/** Inline stroke icons (Lucide paths, 24x24). */
const P: Record<string, string> = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  check: 'M20 6 9 17l-5-5',
  x: 'M18 6 6 18M6 6l12 12',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M13 8H8M13 12H8M13 16H8',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3',
  code: 'M16 18l6-6-6-8M8 6l-6 6 6 6',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  scale: 'M12 3v18M5 7l7-3 7 3M3 11c0 3.3 2 6 5 6s5-2.7 5-6M13 11c0 3.3 2 6 5 6s5-2.7 5-6',
  globe: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z',
  play: 'M6 4l14 8-14 8z',
  pause: 'M7 4h3v16H7zM14 4h3v16h-3z',
  replay: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5',
  alert: 'M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  link: 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  cpu: 'M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M15 2m-2 0H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zM9 11h6v6H9z',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 11V3M1 14h6M9 8h6M17 16h6',
  layers: 'M12 2 2 7l10 5 10-5M2 17l10 5 10-5M2 12l10 5 10-5',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z',
  menu: 'M4 6h16M4 12h16M4 18h16',
  book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5ZM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5',
  clock: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2',
  down: 'M6 9l6 6 6-6',
  hash: 'M4 9h16M4 15h16M10 3 8 21M16 3l-2 18',
};

@Component({
  selector: 'app-icon',
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" [attr.stroke-width]="stroke()"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path
  [attr.d]="d()"/></svg>`,
  styles: [':host{display:inline-flex;flex:none}'],
})
export class Icon {
  readonly name = input.required<string>();
  readonly size = input<number>(16);
  readonly stroke = input<number>(1.75);
  protected readonly d = computed(() => P[this.name()] ?? '');
}
```

## `ui/src/app/shared/reveal.ts`
```ts
import { Directive, ElementRef, OnDestroy, OnInit, inject } from '@angular/core';

/** Adds `.in` when the element scrolls into view (IntersectionObserver, once).
Pair with class="reveal". */
@Directive({ selector: '[appReveal]' })
export class Reveal implements OnInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private io?: IntersectionObserver;
  ngOnInit(): void {
    const node = this.el.nativeElement;
    if (typeof IntersectionObserver === 'undefined') { node.classList.add('in');
    return; }
    this.io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { node.classList.add('in'); this.io?.disconnect(); }
    }), { threshold: 0.15 });
    this.io.observe(node);
  }
  ngOnDestroy(): void { this.io?.disconnect(); }
}
```

## `ui/src/app/shared/seal.ts`
```ts
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** The RedSeal wax seal (SVG, lit: radial wax gradient, rim, embossed ring text).
*/
@Component({
  selector: 'app-seal',
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 200 200"
role="img" [attr.aria-label]="line1() + ' ' + line2()">
  <defs>
    <radialGradient [attr.id]="id + 'w'" cx="38%" cy="32%" r="75%">
      <stop offset="0" stop-color="#E25A41"/><stop offset=".55" [attr.stop-color]="tone() === 'ok' ? '#2A8A5E' : '#C2361F'"/>
      <stop offset="1" [attr.stop-color]="tone() === 'ok' ? '#155C3B' : '#7E2012'"/>
    </radialGradient>
    <path [attr.id]="id + 'r'" d="M100,100 m-66,0 a66,66 0 1,1 132,0 a66,66 0 1,1 -132,0"/>
  </defs>
  <path d="M100 8c12 0 16 9 27 11s22-3 29 6 1 19 6 29 13 15 11 27-12 14-14 25 6
  21-3 29-19 2-29 7-15 13-27 13-16-9-27-11-22 3-29-6-1-19-6-29-13-15-11-27 12-14
  14-25-6-21 3-29 19-2 29-7 15-13 27-13z"
  [attr.fill]="'url(#' + id + 'w)'"/>
  <circle cx="100" cy="100" r="74" fill="none" stroke="rgba(255,255,255,.28)"
  stroke-width="1.5"/>
  <circle cx="100" cy="100" r="56" fill="none" stroke="rgba(0,0,0,.18)"
  stroke-width="1"/>
  <text font-family="Geist Mono Variable, monospace" font-size="11"
  letter-spacing="3.2" fill="rgba(255,255,255,.82)">
    <textPath [attr.href]="'#' + id + 'r'" startOffset="0">REDSEAL · VERIFIED BY
    THE ENGINE · REDSEAL · AUDIT ·</textPath>
  </text>
  <text x="100" y="97" text-anchor="middle" font-family="Instrument Serif, serif"
  font-size="25" fill="#FFF6EE">{{ line1() }}</text>
  <text x="100" y="121" text-anchor="middle" font-family="Geist Variable,
  sans-serif" font-weight="600" font-size="11.5" letter-spacing="1.6" fill="rgba
  (255,246,238,.9)">{{ line2() }}</text>
</svg>
`,
styles: [':host{display:inline-block;filter:drop-shadow(0 10px 14px rgba(120,30,10,.28))}']
})
export class Seal {
  readonly size = input(150);
  readonly line1 = input('Not robust');
  readonly line2 = input('DECISION REQUIRED');
  readonly tone = input<'rs' | 'ok'>('rs');
  protected readonly id = 's' + Math.random().toString(36).slice(2, 8);
}
```

## `ui/src/app/pages/hero-doc.ts`
```ts
import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { Icon } from '../shared/icon';
import { Seal } from '../shared/seal';

type Row = { name: string; color: string; value: number; label: string; note?: string };
type Stage = { tab: string; who: 'paper' | 'tc' | 'rs'; title: string; metric: string; lo: number; hi: number; rows: Row[]; explain: string };

/** First-view story for a first-time visitor, in plain words, with the real case numbers:
 *  1. on paper -> MetroLink has the lowest price per km
 *  2. TrueCost -> over 12 years (price rises included) GreenMetro is cheaper
 *  3. RedSeal -> GreenMetro's own bid says "Sixty Six" in words; at 66 MetroLink wins -> decision required
 * Bidders slide into rank order at each stage. The user moves between stages by clicking the tabs.
 */
const STAGES: Stage[] = [
  {
    tab: 'Price on paper', who: 'paper',
    title: 'On paper, MetroLink is the cheapest.',
    metric: 'Quoted price · ₹ per km',
    lo: 58, hi: 67,
    rows: [
      { name: 'GreenMetro', color: '#2F7D5B', value: 63.0, label: '₹63.00' },
      { name: 'MetroLink', color: '#2447D8', value: 61.0, label: '₹61.00' },
      { name: 'UrbanDrive', color: '#8A6F3E', value: 65.5, label: '₹65.50' },
    ],
    explain: 'A normal comparison just picks the lowest price per km, so MetroLink would get the contract. But a bus contract runs 12 years, and prices rise.',
  },
  {
    tab: 'TrueCost', who: 'tc',
    title: 'Over 12 years, GreenMetro is ₹13.6 cr cheaper.',
    metric: 'Real 12-year cost · ₹ crore, today\u2019s value',
    lo: 530, hi: 585,
    rows: [
      { name: 'GreenMetro', color: '#2F7D5B', value: 549.02, label: '₹549.02 cr', note: 'prices rise slowly' },
      { name: 'MetroLink', color: '#2447D8', value: 562.64, label: '₹562.64 cr', note: '70% tied to inflation' },
      { name: 'UrbanDrive', color: '#8A6F3E', value: 575.23, label: '₹575.23 cr' },
    ],
    explain: 'TrueCost reads every bid and its price-rise formula, fetches official inflation data, and adds up what each bid will really cost. The winner changes.',
  },
  {
    tab: 'RedSeal', who: 'rs',
    title: 'But GreenMetro\u2019s own bid says ₹66, not ₹63.',
    metric: 'Real 12-year cost, re-run with ₹66 · ₹ crore',
    lo: 530, hi: 585,
    rows: [
      { name: 'GreenMetro', color: '#2F7D5B', value: 575.17, label: '₹575.17 cr', note: 'at ₹66 / km' },
      { name: 'MetroLink', color: '#2447D8', value: 562.64, label: '₹562.64 cr' },
      { name: 'UrbanDrive', color: '#8A6F3E', value: 575.23, label: '₹575.23 cr' },
    ],
    explain: 'RedSeal tries to break the award. GreenMetro wrote ₹63.00 in figures but "Sixty Six" in words, and the tender says words win. Re-run at ₹66: MetroLink wins.',
  },
];

@Component({
  selector: 'app-hero-doc',
  imports: [Seal, Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<div class="stage" [attr.data-who]="s().who">
  <div class="sheet-shadow"></div>
  <article class="card" aria-label="The e-bus tender in three steps">
    <div class="kicker">REAL PUBLIC TENDER 1376/CRUT · ODISHA, INDIA</div>
    <p class="about">The state transport body is hiring an operator to buy, run and maintain <b>200 electric buses</b> for <b>12 years</b>, paid per km driven. Three operators bid. Who should win?</p>

    <div class="tabs" role="tablist">
      @for (st of stages; track st.tab; let i = $index) {
        @if (i > 0) { <app-icon class="sep" [class.lit]="i <= idx()" name="arrow" [size]="13" aria-hidden="true"/> }
        <button type="button" role="tab" class="tab" [class.next]="i === idx() + 1" [class.on]="i === idx()" [class.done]="i < idx()" [attr.aria-selected]="i === idx()" [attr.data-who]="st.who" (click)="go(i)">
          <span class="n">{{ i + 1 }}</span>{{ st.tab }}
        </button>
      }
    </div>

    <h3 class="title">{{ s().title }}</h3>
    <div class="metric">{{ s().metric }}</div>

    <div class="board" [style.height.px]="rows().length * 52">
      @for (r of rows(); track r.name) {
        <div class="row" [style.transform]="'translateY(' + r.rank * 52 + 'px)'" [class.win]="r.rank === 0">
          <span class="nm"><i class="dot" [style.background]="r.color"></i>{{ r.name }}</span>
          <span class="track"><span class="bar" [style.width.%]="r.w" [style.background]="r.color"></span></span>
          @if (r.note) { <span class="note">{{ r.note }}</span> }
          <span class="val mono">{{ r.label }}</span>
          <span class="badge">{{ r.rank === 0 ? (idx() === 0 ? 'Lowest' : 'Cheapest') : '' }}</span>
        </div>
      }
    </div>

    @if (idx() === 2) {
      <div class="evidence">
        <span class="ev-1">From GreenMetro\u2019s bid, page 1</span>
        <span class="ev-row"><span class="mono struck">Rs 63.00 / km</span><span class="mono words">"Rupees Sixty Six only"</span></span>
      </div>
    }

    <p class="explain">{{ s().explain }}</p>
    <div class="seal-slot" [class.in]="idx() === 2"><app-seal [size]="124"/></div>
  </article>

  <div class="foot">
    @if (idx() > 0) {
      <button class="replay" type="button" (click)="go(0)" aria-label="Back to the first step">
        <app-icon name="replay" [size]="14"/> Start over
      </button>
    }
    <span class="answer" [class.in]="idx() === 2"><b>AwardShield\u2019s answer:</b> The award is not safe. The committee must decide which price counts before signing.</span>
  </div>
</div>
`,
styles: [`
  :host { display: block; overflow-x: clip; overflow-y: visible; }
  .stage { position: relative; padding: 14px 22px 8px 0; }
  .sheet-shadow { position: absolute; inset: 28px 40px 70px 20px; background: var(--paper-2); border: 1px solid var(--rule); border-radius: 18px; transform: rotate(-2.2deg); }
  .card { position: relative; background: var(--sheet); border: 1px solid var(--rule); border-radius: 18px; padding: 22px 26px 20px; box-shadow: var(--shadow-doc), inset 0 1px 0 #fff; min-height: 568px; }
  .kicker { font: 600 10.5px/1.3 var(--mono); letter-spacing: .1em; color: var(--ink-3); padding-right: 90px; }
  .about { margin: 8px 0 0; font-size: 14px; line-height: 1.5; color: var(--ink-2); padding-right: 70px; } .about b { color: var(--ink); font-weight: 600; }
  .sep { color: var(--ink-4, #b9b4a8); flex: none; transition: color 300ms; } .sep.lit { color: var(--ink-2); }
  .tab.next { color: var(--ink-2); box-shadow: inset 0 0 1px var(--rule-2); }
  .tab.next:hover { background: var(--sheet); color: var(--ink); }
  .tabs { display: flex; align-items: center; gap: 4px; margin: 14px 0 16px; padding: 4px; background: var(--paper); border: 1px solid var(--rule); border-radius: 999px; width: fit-content; max-width: 100%; }
  .tab { border: 0; background: transparent; border-radius: 999px; padding: 7px 7px 8px; font: 500 12.5px/1 var(--sans); color: var(--ink-3); cursor: pointer; display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; transition: background 250ms, color 250ms; }
  .tab .n { width: 18px; height: 18px; border-radius: 50%; display: inline-grid; place-items: center; font: 600 10.5px/1 var(--mono); background: var(--rule); color: var(--ink-2); }
  .tab.on { background: var(--sheet); color: var(--ink); box-shadow: var(--shadow-2); }
  .tab.on[data-who='paper'] .n, .tab.done[data-who='paper'] .n { background: var(--ink); color: #fff; }
  .tab.on[data-who='tc'] .n, .tab.done[data-who='tc'] .n { background: var(--tc); color: #fff; }
  .tab.on[data-who='rs'] .n { background: var(--rs); color: #fff; }

  .title { font: 400 30px/1.12 var(--serif); letter-spacing: -.01em; margin: 0 6px; color: var(--ink); min-height: 34px; animation: fade 450ms var(--ease-out); }
  [data-who='tc'] .title { color: var(--tc-700); } [data-who='rs'] .title { color: var(--rs-700); }
  .metric { font: 600 10.5px/1.2 var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); margin-bottom: 10px; }
  .board { position: relative; transition: height 300ms; }
  .row { position: absolute; left: 0; right: 0; top: 0; height: 46px; display: grid; grid-template-columns: 104px minmax(0, 1fr) 92px 80px; align-items: center; gap: 12px; padding: 0 10px; border-radius: 10px; transition: transform 650ms var(--ease-out), background 300ms; }
  .row.win { background: var(--paper); }
  .nm { font: 600 13.5px/1 var(--sans); color: var(--ink); display: inline-flex; align-items: center; gap: 8px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; flex: none; }
  .track { position: relative; height: 10px; background: var(--rule); border-radius: 999px; }
  .bar { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; transition: width 700ms var(--ease-out); opacity: .9; }
  .note { position: absolute; left: 0; top: 14px; font: 500 11px/1 var(--sans); color: var(--ink-3); white-space: nowrap; }
  .val { font-size: 13.5px; text-align: right; color: var(--ink); }
  .badge { font: 600 11px/1 var(--sans); color: var(--ok); #2F7D5B; text-align: right; }
  .row.win .badge:not(:empty):before { content: '\2713 '; }

  .evidence { margin-top: 10px; padding: 10px 12px; border: 1px dashed var(--rs-100); background: var(--rs-50); border-radius: 10px; display: grid; gap: 6px; animation: fade 450ms var(--ease-out); }
  .ev-1 { font: 600 10px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--rs-700); }
  .ev-row { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; font-size: 13px; }
  .struck { text-decoration: line-through; text-decoration-color: var(--rs); text-decoration-thickness: 2px; color: var(--ink-2); }
  .words { background: linear-gradient(transparent 55%, rgba(194,54,31,.22) 55%); padding: 0 3px; color: var(--ink); }
  .explain { margin: 14px 0 0; font-size: 14px; line-height: 1.55; color: var(--ink-2); min-height: 66px; animation: fade 450ms var(--ease-out); }
  .seal-slot { position: absolute; right: -30px; top: -42px; opacity: 0; transform: scale(1.7) rotate(-26deg); transition: opacity 260ms ease, transform 520ms var(--ease-seal); pointer-events: none; }
  .seal-slot.in { opacity: 1; transform: scale(1) rotate(-12deg); transition-delay: 600ms; }
  .foot { display: flex; align-items: center; gap: 14px; margin-top: 14px; }
  .replay { flex: none; border: 1px solid var(--rule-2); background: var(--sheet); border-radius: 999px; padding: 6px 12px; font: 500 12.5px/1 var(--sans); color: var(--ink-3); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
  .replay:hover { color: var(--ink); }
  .answer { font-size: 13px; line-height: 1.45; color: var(--ink-2); opacity: 0; transform: translateY(4px); transition: opacity 400ms 900ms, transform 400ms; }
  .answer.in { opacity: 1; transform: none; } .answer b { color: var(--rs-700); }
  @keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  @media (max-width: 900px) {
    .stage { padding: 30px 0 4px; } .sheet-shadow { display: none; } .card { padding: 18px 16px; min-height: 0; }
    .seal-slot { right: -6px; top: -40px; } .seal-slot app-seal { width: 96px; } .title { font-size: 25px; }
  }
  @media (max-width: 520px) {
    .tab { padding: 6px 8px 6px 6px; font-size: 11.5px; gap: 5px; } .sep { display: none; } .tabs { gap: 2px; } .tab.n { width: 16px; height: 16px; }
    .about { padding-right: 0; font-size: 13.5px; }
    .row { grid-template-columns: 88px minmax(0, 1fr) 82px; gap: 8px; padding: 0 6px; } .badge { display: none; }
    .nm, .val { font-size: 12.5px; } .note { display: none; }
  }
  @media (max-width: 360px) { .tab { font-size: 10.5px; padding: 5px 6px 5px 5px; gap: 4px; } .tab.n { display: none; } }
`] })
export class HeroDoc {
  protected readonly stages = STAGES;
  protected readonly idx = signal(0);
  protected readonly s = computed(() => STAGES[this.idx()]);
  protected readonly rows = computed(() => {
    const st = this.s();
    const order = [...st.rows].sort((a, b) => a.value - b.value).map((r) => r.name);
    return st.rows.map((r) => ({
      ...r, rank: order.indexOf(r.name),
      w: 18 + 82 * Math.max(0, Math.min(1, (r.value - st.lo) / (st.hi - st.lo))),
    }));
  });
  go(i: number): void { this.idx.set(i); }
}
```

## `ui/src/app/pages/acts.ts`
```ts
import { ChangeDetectionStrategy, Component, OnDestroy, computed, input, signal } from '@angular/core';
import { CaseOverview, BIDDER_COLOR } from '../core/api';
import { Chart, INK } from '../shared/chart';

type Act = 0 | 1 | 2;

/** One horizontal bar chart that morphs through three readings of the same bids:
 * quoted rate (₹/km) -> 12-year cost -> 12-year cost after RedSeal's verified correction.
 */
@Component({
  selector: 'app-acts',
  imports: [Chart],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<div class="acts">
  <div class="top">
    <div class="seg" role="tablist" aria-label="Three readings of the same bids">
      @for (a of labels; track a.k; let i = $index) {
        <button role="tab" type="button" [class.on]="act() === i" [attr.aria-selected]="act() === i" (click)="go($any(i))">
          <span class="n mono">{{ i + 1 }}</span> {{ a.k }}
        </button>
      }
    </div>
    <button class="auto" type="button" (click)="autoplay()" [attr.aria-label]="playing() ? 'Playing' : 'Play the three acts'">
      {{ playing() ? 'Playing…' : '\u25B6 Play all three' }}
    </button>
  </div>
  <div class="cap" aria-live="polite">
    <div class="winner"><span class="overline">{{ labels[act()].k }} \u2013 winner</span>
      <b [style.color]="color(winner())">{{ winner() }}</b>
    </div>
    <p>{{ labels[act()].why }}</p>
  </div>
  <app-chart [options]="options()" height="250"/>
</div>
`,
styles: [`
  .acts { display: grid; gap: var(--s4); }
  .top { display: flex; align-items: center; gap: var(--s4); flex-wrap: wrap; }
  .seg button { display: inline-flex; gap: 8px; align-items: center; }
  .n { width: 20px; height: 20px; border-radius: 50%; display: inline-grid; place-items: center; font-size: 11px; background: var(--paper-2); border: 1px solid var(--rule); }
  .seg button.on .n { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .auto { border: 0; background: transparent; color: var(--tc); font: 500 14px/1 var(--sans); cursor: pointer; }
  .cap { display: grid; gap: 4px; } .winner b { font: 600 22px/1.1 var(--sans); letter-spacing: -0.02em; }
  .cap p { color: var(--ink-2); font-size: 15px; }
  @media (max-width: 640px) { .cap { grid-template-columns: 1fr; gap: var(--s2); } .seg button { padding: 7px 10px; font-size: 13px; } }
`] })
export class Acts implements OnDestroy {
  readonly data = input.required<CaseOverview>();
  protected readonly act = signal<Act>(0);
  protected readonly playing = signal(false);
  private t: ReturnType<typeof setTimeout>[] = [];

  protected readonly labels = [
    { k: 'Quoted rate', why: 'Read the price on page one and MetroLink is cheapest: ₹61.00 a kilometre.' },
    { k: '12-year cost', why: '70% of MetroLink\u2019s price rises with inflation every six months. Over twelve years, in today\u2019s money, GreenMetro is cheaper.' },
    { k: 'After RedSeal', why: '\u201cGreenMetro\u2019s rate in words is \u201cSixty Six\u201d, not 63.00. The tender says words prevail. Re-run: MetroLink wins.' },
  ];

  protected readonly rows = computed(() => {
    const d = this.data(); const a = this.act();
    if (a === 0) return d.bidders.map((b) => ({ name: b.name, v: b.rate })).sort((x, y) => x.v - y.v);
    const r = a === 1 ? d.acts.lifetime.ranking : (d.acts.after?.ranking ?? d.acts.lifetime.ranking);
    return r.map(([name, v]) => ({ name, v }));
  });
  protected readonly winner = computed(() => this.rows()[0]?.name ?? '');
  protected color(n: string) { return BIDDER_COLOR[n] ?? INK.ink; }

  protected readonly options = computed(() => {
    const rows = [...this.rows()].reverse(); // top = cheapest
    const a = this.act();
    const unit = a === 0 ? (v: number) => `₹${v.toFixed(2)}/km` : (v: number) => `₹${v.toFixed(2)} cr`;
    const vals = rows.map((r) => r.v);
    const min = Math.min(...vals), max = Math.max(...vals);
    const pad = (max - min) * 0.9 || 1;
    const w = this.winner();
    const after = this.data().acts.after;
    return {
      ...chartBase(),
      grid: { left: 8, right: 120, top: 6, bottom: 6, containLabel: true },
      xAxis: { type: 'value', min: Math.floor(min - pad), max: Math.ceil(max + pad * 0.2), show: false },
      yAxis: { type: 'category', data: rows.map((r) => r.name), ...axis(), axisLabel: { color: INK.ink, fontSize: 14, fontFamily: 'Geist Variable, sans-serif', fontWeight: 500 }, axisLine: { show: false } },
      series: [{
        name: 'value', type: 'bar', barWidth: 26, realtimeSort: false,
        data: rows.map((r) => ({
          value: r.v,
          itemStyle: {
            color: this.color(r.name), borderRadius: [0, 6, 6, 0],
            opacity: r.name === w ? 1 : 0.42,
            borderColor: a === 2 && after && r.name === this.data().acts.after?.winner ? INK.rs : 'transparent',
            borderWidth: a === 2 && after && r.name === this.data().acts.after?.winner ? 2 : 0,
            borderType: 'dashed',
          },
        })),
        label: {
          show: true, position: 'right', fontFamily: 'Geist Mono Variable, monospace', fontSize: 13, color: INK.ink,
          formatter: (p: { value: number; name: string }) => unit(p.value) + (p.name === w ? ' \u2605' : ''),
        },
      }],
      tooltip: { show: false },
    };
  });

  go(a: Act): void { this.stop(); this.act.set(a); }
  autoplay(): void {
    this.stop(); this.playing.set(true);
    this.t.push(setTimeout(() => this.act.set(1), 2600), setTimeout(() => this.act.set(2), 5600), setTimeout(() => this.playing.set(false), 6200));
  }
  private stop(): void { this.t.forEach(clearTimeout); this.t = []; this.playing.set(false); }
  ngOnDestroy(): void { this.stop(); }
}
```

## `ui/src/app/pages/landing.ts`
```ts
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CASE_ID } from '../core/api';
import { Icon } from '../shared/icon';
import { Reveal } from '../shared/reveal';
import { Seal } from '../shared/seal';
import { HeroDoc } from './hero-doc';

@Component({
  selector: 'app-landing',
  imports: [RouterLink, Icon, Reveal, Seal, HeroDoc],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<section class="hero">
  <div class="wrap hero-grid">
    <div class="copy">
      <span class="pill rise" style="--i:0"><i class="dot" style="color:var(--rs)"></i> Public tender audit · Gemini & Google ADK</span>
      <h1 class="display big rise" style="--i:1">The cheapest bid<br>is not always the <em>cheapest.</em></h1>
      <p class="lead rise" style="--i:2">
        <b>TrueCost</b> reads every bid and works out what each will really cost over the whole contract.<br>
        <b>RedSeal</b> then tries to break that award, and proves every objection by re-running the numbers.
      </p>
      <div class="row ctas rise" style="--i:3">
        <a class="btn" routerLink="/case/{{CASE_ID}}">See the e-bus audit <span class="ico"><app-icon name="arrow"/></span></a>
      </div>
      <dl class="facts rise" style="--i:4">
        <div><dt class="overline">Tender</dt><dd>E-bus operations, 12 years</dd></div>
        <div><dt class="overline">Bids</dt><dd class="mono">3</dd></div>
        <div><dt class="overline">At stake</dt><dd class="mono">₹13.61 cr</dd></div>
      </dl>
    </div>
    <app-hero-doc class="rise" style="--i:2"/>
  </div>
</section>

<!-- TWO PARTS -->
<section class="section band">
  <div class="wrap">
    <div class="sh center reveal" appReveal>
      <span class="overline">Two agents, two jobs</span>
      <h2 class="display">One builds the case. <em>One attacks it.</em></h2>
    </div>
    <div class="grid-2 parts">
      <a class="part tcp card hoverable reveal" appReveal routerLink="/case/{{CASE_ID}}/truecost">
        <div class="ph-h"><span class="pill tc"><i class="dot"></i> Part one</span><app-icon name="arrow" [size]="18"/></div>
        <h3 class="name serif">TrueCost</h3>
        <p class="lead">Reads the tender and every bid. Pulls rates, formulas and indices, each with a verbatim quote, a page number and a live government source.</p>
        <ul class="ticks">
          <li><app-icon name="check" [size]="15"/> Gemini agents in parallel, one per bidder</li>
          <li><app-icon name="check" [size]="15"/> Price indices fetched and frozen with a hash</li>
          <li><app-icon name="check" [size]="15"/> Engine projects 144 months, discounted</li>
        </ul>
        <div class="eg mono"><span class="quote">&#34;0.64 + 0.12·CPI-IW + 0.14·WPI...&#34;</span><span class="src">BID_1 p.3</span></div>
      </a>

      <a class="part rsp card hoverable reveal" appReveal routerLink="/case/{{CASE_ID}}/redseal">
        <div class="ph-h"><span class="pill rs"><i class="dot"></i> Part two</span><app-icon name="arrow" [size]="18"/></div>
        <h3 class="name serif">RedSeal</h3>
        <p class="lead">An adversarial auditor. It hunts for anything that could change the winner, then lets the engine decide whether the objection actually matters.</p>
        <ul class="ticks">
          <li><app-icon name="check" [size]="15"/> Words vs figures, tender rules, terms</li>
          <li><app-icon name="check" [size]="15"/> Every challenge re-run, not argued</li>
          <li><app-icon name="check" [size]="15"/> How far each bid can move before the winner flips</li>
        </ul>
        <div class="seal-mini"><app-seal [size]="92"/></div>
      </a>
    </div>
  </div>
</section>

<!-- PIPELINE -->
<section class="section" id="how">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline">How it works</span>
      <h2 class="display">The AI builds the inputs. <em>Code decides.</em></h2>
      <p class="lead muted">Language models are good at reading messy documents and bad at arithmetic. So they never rank a bid. A deterministic engine does every sum.</p>
    </div>
    <ol class="rail reveal" appReveal>
      @for (s of steps; track s.t; let i = $index) {
        <li class="step" [class]="'step ' + s.k">
          <div class="badge"><app-icon [name]="s.icon" [size]="18"/></div>
          <div class="kind mono">{{ s.kind }}</div>
          <div class="t">{{ s.t }}</div>
          <p class="small muted">{{ s.d }}</p>
        </li>
      }
    </ol>
  </div>
</section>

<!-- VERDICT RULES -->
<section class="section band">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline">Three possible verdicts</span>
      <h2 class="display">RedSeal can only say <em>what the engine proves.</em></h2>
    </div>
    <div class="grid-3">
      @for (v of verdicts; track v.t; let i = $index) {
        <div class="card card-b verdict reveal" appReveal [class.cur]="v.cur">
          <span class="pill" [class]="'pill ' + v.tone"><i class="dot"></i> {{ v.t }}</span>
          <p>{{ v.d }}</p>
          @if (v.cur) { <span class="now small"><app-icon name="alert" [size]="14"/> This case</span> }
        </div>
      }
    </div>
  </div>
</section>

<!-- GOOGLE STACK -->
<section class="section console stack">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline" style="color:var(--console-ink-2)">Built with Google AI</span>
      <h2 class="display">A multi-agent system, <em>not a prompt.</em></h2>
    </div>
    <div class="tiles">
      @for (g of google; track g.t) {
        <div class="tile reveal" appReveal>
          <span class="gdot" [style.background]="g.c"></span>
          <div class="t">{{ g.t }}</div>
          <p class="small">{{ g.d }}</p>
        </div>
      }
    </div>
  </div>
</section>

<!-- CTA -->
<section class="section">
  <div class="wrap">
    <div class="bezel reveal" appReveal><div class="core cta">
      <div>
        <h2 class="display">Open the audit.</h2>
        <p class="lead muted">Start with the decision. Then go as deep as you want: the evidence, the engine, the challenges, the agent run.</p>
      </div>
      <div class="row wrapr">
        <a class="btn" routerLink="/case/{{CASE_ID}}">Decision brief <span class="ico"><app-icon name="arrow"/></span></a>
        <a class="btn btn-ghost" routerLink="/case/{{CASE_ID}}/run">Watch the agents <span class="ico"><app-icon name="play"/></span></a>
      </div>
    </div></div>
  </div>
</section>
`,
styles: [`
  .hero { padding: var(--s16) 0 var(--s20); overflow: hidden; }
  .hero-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); gap: var(--s16); align-items: center; }
  .copy { display: grid; gap: var(--s6); justify-items: start; }
  .big { font-size: clamp(42px, 5.6vw, 76px); line-height: .98; letter-spacing: -0.025em; }
  .tc { color: var(--tc); font-weight: 600; } .rs { color: var(--rs); font-weight: 600; }
  .ctas { flex-wrap: wrap; }
  .facts { display: flex; gap: var(--s10); margin: var(--s2) 0 0; padding-top: var(--s5); border-top: 1px solid var(--rule); }
  .facts dd { margin: 4px 0 0; color: var(--ink); font-weight: 500; }

  .sh { display: grid; gap: var(--s4); max-width: 720px; margin-bottom: var(--s12); }
  .sh.center { margin-left: auto; margin-right: auto; text-align: center; justify-items: center; }
  .more { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; }
  .rail { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: var(--s3); position: relative; }
  .rail::before { content: ''; position: absolute; left: 6%; right: 6%; top: 22px; border-top: 1.5px dashed var(--rule-2); z-index: 0; }
  .step { position: relative; z-index: 1; display: grid; gap: 6px; align-content: start; }
  .badge { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; background: var(--sheet); border: 1px solid var(--rule); color: var(--ink); box-shadow: var(--shadow-1); margin-bottom: 8px; }
  .step.ai .badge { background: var(--tc-50); border-color: var(--tc-100); color: var(--tc); }
  .step.code .badge { background: var(--console); border-color: var(--console); color: var(--console-ink); }
  .step.rsk .badge { background: var(--rs-50); border-color: var(--rs-100); color: var(--rs); }
  .step.out .badge { background: var(--ink); color: var(--paper); }
  .kind { font-size: 10.5px; letter-spacing: .1em; color: var(--ink-3); }
  .step.t { font: 600 16px/1.3 var(--sans); color: var(--ink); }

  .parts { gap: var(--s6); }
  .part { display: grid; gap: var(--s4); padding: var(--s8); color: inherit; text-decoration: none !important; position: relative; overflow: hidden; align-content: start; }
  .ph-h { display: flex; justify-content: space-between; align-items: center; color: var(--ink-3); }
  .name { font-size: 54px; line-height: 1; letter-spacing: -0.02em; color: var(--ink); }
  .tcp { border-top: 3px solid var(--tc); } .rsp { border-top: 3px solid var(--rs); }
  .ticks { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; font-size: 14.5px; }
  .ticks li { display: flex; gap: 8px; align-items: center; } .tcp .ticks app-icon { color: var(--tc); } .rsp .ticks app-icon { color: var(--rs); }
  .eg { margin-top: var(--s2); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .seal-mini { position: absolute; right: 22px; bottom: 18px; transform: rotate(-12deg); }

  .verdict { display: grid; gap: var(--s3); align-content: start; }
  .verdict p { font-size: 15px; }
  .verdict.cur { border-color: var(--rs-100); box-shadow: 0 0 4px var(--rs-50); }
  .now { display: inline-flex; gap: 6px; align-items: center; color: var(--rs); font-weight: 600; }

  .stack { border-radius: var(--r4); margin: 0 var(--s4); }
  .tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--console-line); border: 1px solid var(--console-line); border-radius: var(--r3); overflow: hidden; }
  .tile { background: var(--console); padding: var(--s6); display: grid; gap: 8px; align-content: start; }
  .tile .t { color: var(--console-ink); font: 600 16px/1.3 var(--sans); }
  .gdot { width: 10px; height: 10px; border-radius: 3px; }

  .cta { padding: var(--s12); display: flex; justify-content: space-between; align-items: center; gap: var(--s8); }
  .cta > div:first-child { display: grid; gap: var(--s3); max-width: 560px; }
  .wrapr { flex-wrap: wrap; }

  @media (max-width: 1000px) {
    .hero-grid { grid-template-columns: minmax(0, 1fr); gap: var(--s10); }
    .rail { grid-template-columns: minmax(0, 1fr); gap: var(--s5); }
    .rail::before { left: 22px; right: auto; top: 0; bottom: 0; border-top: 0; border-left: 1.5px dashed var(--rule-2); }
    .step { grid-template-columns: 44px minmax(0, 1fr); column-gap: var(--s4); align-items: center; }
    .badge { grid-row: span 3; margin: 0; }
    .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .cta { flex-direction: column; align-items: flex-start; padding: var(--s8); }
  }
  @media (max-width: 560px) {
    .hero { padding-top: var(--s10); } .facts { gap: var(--s6); grid-template-columns: minmax(0, 1fr); }
    .tiles { grid-template-columns: minmax(0, 1fr); }
    .stack { margin: 0; border-radius: 0; } .name { font-size: 44px; } .part { padding: var(--s6); }
    .seal-mini { display: none; }
  }
`] })
export class Landing {
  protected readonly steps = [
    { k: 'in', kind: 'INPUT', icon: 'file', t: 'Tender & bids', d: 'PDFs exactly as the buyer received them.' },
    { k: 'ai', kind: 'AI · GEMINI', icon: 'search', t: 'TrueCost', d: 'Extracts every rate, formula and index, each quoted and sourced.' },
    { k: 'code', kind: 'CODE', icon: 'code', t: 'Engine', d: '144 months of escalation, discounted. Same inputs, same answer.' },
    { k: 'rsk', kind: 'AI + PROOF', icon: 'shield', t: 'RedSeal', d: 'Challenges the award. Only engine re-runs count as proof.' },
    { k: 'out', kind: 'OUTPUT', icon: 'scale', t: 'Verdict', d: 'Robust, understated or not robust, with a proof pack.' },
  ];
  protected readonly verdicts = [
    { t: 'Certified robust', tone: 'ok', cur: false, d: 'No verified challenge changes the winner, and no bid sits near its flip point.' },
    { t: 'Understated', tone: 'warn', cur: false, d: 'The winner holds, but the true cost or the margin is materially different from what was reported.' },
    { t: 'Not robust · decision required', tone: 'rs', cur: true, d: 'A credible reading of the tender changes the winner. The buyer must decide which reading applies.' },
  ];
  protected readonly google = [
    { c: 'var(--g-blue)', t: 'Gemini', d: 'Reads PDFs, extracts terms, writes challenges and the final narrative.' },
    { c: 'var(--g-red)', t: 'ADK SequentialAgent', d: 'Orchestrates read -> model -> finalise, and the RedSeal hunt.' },
    { c: 'var(--g-yellow)', t: 'ADK ParallelAgent', d: 'One commercial agent per bidder, running at the same time.' },
    { c: 'var(--g-green)', t: 'Vertex AI web grounding', d: 'Finds the official index publisher for each cost driver.' },
  ];
}
```

## `ui/src/app/pages/case-shell.ts`
```ts
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

/** Shared header for every case page: breadcrumb, title, sub-navigation across the parts. */
@Component({
  selector: 'app-case-head',
  imports: [RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<div class="wrap head">
  <nav class="crumbs small" aria-label="Breadcrumb">
    <a routerLink="/">AwardShield</a><span>/</span><a [routerLink]="['/case', id()]">{{ id() }}</a>
    @if (part()) { <span>/</span><span class="cur">{{ part() }}</span> }
  </nav>
  <div class="row top">
    <div class="tt">
      <span class="overline" [style.color]="tone()">{{ kicker() }}</span>
      <h1 class="display">{{ title() }}</h1>
      @if (sub()) { <p class="lead muted">{{ sub() }}</p> }
    </div>
  </div>
  <nav class="tabs" aria-label="Case sections">
    <a [routerLink]="['/case', id()]" routerLinkActive="on" [routerLinkActiveOptions]="{ exact: true }">Decision</a>
    <a [routerLink]="['/case', id(), 'truecost']" routerLinkActive="on"><i class="d tc"></i>TrueCost</a>
    <a [routerLink]="['/case', id(), 'engine']" routerLinkActive="on"><i class="d ink"></i>Engine</a>
    <a [routerLink]="['/case', id(), 'redseal']" routerLinkActive="on"><i class="d rs"></i>RedSeal</a>
    <a [routerLink]="['/case', id(), 'run']" routerLinkActive="on">Agent run</a>
  </nav>
</div>
`,
styles: [`
  .head { padding-top: var(--s10); display: grid; gap: var(--s6); }
  .crumbs { display: flex; gap: 8px; color: var(--ink-3); flex-wrap: wrap; }
  .crumbs a { color: var(--ink-3); } .cur { color: var(--ink); }
  .tt { display: grid; gap: var(--s3); max-width: 820px; }
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--rule); overflow-x: auto; scrollbar-width: none; }
  .tabs a { padding: 12px 14px; color: var(--ink-3); font: 500 14.5/1 var(--sans); border-bottom: 2px solid transparent; margin-bottom: -1px; display: inline-flex; gap: 7px; align-items: center; white-space: nowrap; text-decoration: none !important; }
  .tabs a:hover { color: var(--ink); } .tabs a.on { color: var(--ink); border-bottom-color: var(--ink); }
  .d { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
  .tc { background: var(--tc); } .rs { background: var(--rs); } .d.ink { background: var(--ink); }
`] })
export class CaseHead {
  readonly id = input.required<string>();
  readonly part = input('');
  readonly kicker = input('');
  readonly title = input.required<string>();
  readonly sub = input('');
  readonly tone = input('var(--ink-3)');
}
```

## `ui/src/app/pages/decision.ts`
```ts
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, of, switchMap } from 'rxjs';
import { Api, BIDDER_COLOR, CaseOverview, cr, inr } from '../core/api';
import { Icon } from '../shared/icon';
import { Seal } from '../shared/seal';
import { Acts } from './acts';
import { CaseHead } from './case-shell';

@Component({
  selector: 'app-decision',
  imports: [RouterLink, Icon, Seal, Acts, CaseHead],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<app-case-head [id]="id()" kicker="Decision brief" [title]="d()?.title || 'Loading...'"
  [sub]="d() ? (d()!.buyer + ' · ' + (d()!.months / 12) + '-year contract from ' + d()!.start) : ''"/>

@if (d(); as d) {
  <section class="wrap body">
    <!-- verdict -->
    <div class="bezel rise"><div class="core verdict">
      <div class="vcopy">
        <span class="pill" [class]="'pill ' + tone()">{{ statusLabel() }}</span>
        <h2 class="display vh">{{ headline() }}</h2>
        <p class="lead">{{ d.verdict?.narrative?.recommendation || d.verdict?.summary }}</p>
      </div>
      <app-seal [size]="168" [line1]="sealText()[0]" [line2]="sealText()[1]" [tone]="tone() === 'ok' ? 'ok' : 'rs'"/>
    </div></div>

    <!-- outcomes -->
    @if (d.verdict?.status === 'OVERTURNED') {
      <div class="blk">
        <div class="bh"><span class="overline">The buyer\u2019s decision</span><h3 class="h1">Which reading of the tender applies?</h3></div>
        <div class="grid-3">
          @for (o of outcomes(); track o.rule; let i = $index) {
            <div class="card card-b oc rise" [style.--i]="i">
              <span class="small muted">If...</span>
              <div class="rule">{{ o.rule }}</div>
              <div class="arrow"><app-icon name="arrow" [size]="14"/> winner</div>
              <div class="win" [style.color]="color(o.winner)">{{ o.winner }}</div>
              <p class="small muted">{{ o.why }}</p>
            </div>
          }
        </div>
      </div>
    }

    <!-- three acts -->
    <div class="blk card card-b"><app-acts [data]="d"/></div>

    <!-- bidders -->
    <div class="blk">
      <div class="bh"><span class="overline">The bids</span><h3 class="h1">Three operators, three price structures</h3></div>
      <div class="card tbl">
        <table class="dtable">
          <thead><tr>
            <th>Bidder</th><th class="num">Quoted ₹/km</th><th>Rate in words</th>
            <th class="num">12-yr cost</th><th class="num">Year one</th><th class="num">Price \u00d7, final year</th>
          </tr></thead>
          <tbody>
            @for (b of d.bidders; track b.name) {
              <tr>
                <td><span class="bn"><i [style.background]="color(b.name)"></i>{{ b.name }}</span></td>
                <td class="num">{{ b.rate.toFixed(2) }}</td>
                <td><span class="mono small" [class.flag]="mismatch(b.name)">{{ b.amount_in_words || '-' }}</span></td>
                <td class="num">{{ cr(b.sticker_cr) }}</td>
                <td class="num"><b>{{ cr(b.lifetime_cr) }}</b></td>
                <td class="num">{{ cr(b.year_one_cr) }}</td>
                <td class="num">&#215;{{ b.factor_end.toFixed(3) }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="small muted note">12-year cost = every monthly payment for {{ d.months }} months with each bidder\u2019s own price-adjustment formula, discounted at {{ (d.discount.annual * 100).toFixed(0) }}% a year to today\u2019s money. Quoted-rate cost uses the same volume with no price adjustment.</p>
    </div>

    <!-- go deeper -->
    <div class="blk">
      <div class="bh"><span class="overline">Go deeper</span><h1 class="h1">Check any part yourself</h1></div>
      <div class="deep">
        @for (p of parts; track p.t) {
          <a class="card card-b hoverable dp" [routerLink]="['/case', id(), p.path]" [style.borderTopColor]="p.c">
            <div class="row"><app-icon [name]="p.icon" [size]="18"/><span class="spacer"></span><app-icon name="arrow" [size]="16"/></div>
            <div class="h2">{{ p.t }}</div>
            <p class="small muted">{{ p.d }}</p>
          </a>
        }
      </div>
    </div>
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">{{ failed() ? 'Could not reach the API. Start: uvicorn api.app:app --port 8900' : 'Loading the case...' }}</div></div>
}
`,
styles: [`
  body { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s12); }
  .verdict { display: flex; align-items: center; justify-content: space-between; padding: var(--s10) var(--s12); gap: var(--s12); }
  .vcopy { display: grid; gap: var(--s4); justify-items: start; max-width: 720px; }
  .vh { font-size: clamp(30px, 3.4vw, 46px); }
  .blk { display: grid; gap: var(--s5); }
  .bh { display: grid; gap: 6px; }
  .oc { display: grid; gap: 6px; align-content: start; }
  .rule { font: 600 17px/1.35 var(--sans); color: var(--ink); }
  .arrow { display: inline-flex; gap: 6px; align-items: center; color: var(--ink-3); font-size: 13px; margin-top: 8px; }
  .win { font: 600 26px/1.1 var(--sans); letter-spacing: -0.02em; }
  .tbl { overflow-x: auto; }
  .bn { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; color: var(--ink); } .bn i { width: 10px; height: 10px; border-radius: 3px; }
  .flag { background: var(--rs-50); color: var(--rs-700); padding: 2px 6px; border-radius: 5px; border: 1px solid var(--rs-100); }
  .note { max-width: 860px; }
  .deep { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--s4); }
  .dp { display: grid; gap: var(--s3); color: inherit; text-decoration: none !important; border-top: 3px solid; }
  @media (max-width: 900px) {
    .verdict { flex-direction: column-reverse; align-items: flex-start; padding: var(--s8) var(--s6); }
    .deep { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 560px) { .deep { grid-template-columns: minmax(0, 1fr); } }
`] })
export class Decision {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly failed = computed(() => this.d() === undefined);
  protected readonly d = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.case(id).pipe(catchError(() => of(undefined as CaseOverview | null | undefined)))),
    { initialValue: null as CaseOverview | null | undefined }
  ));
  protected color(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }
  protected readonly tone = computed(() => ({ OVERTURNED: 'rs', UNDERSTATED: 'warn', CERTIFIED_ROBUST: 'ok' }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST']));
  protected readonly statusLabel = computed(() => ({ OVERTURNED: 'Award not robust \u2013 decision required', UNDERSTATED: 'Understated', CERTIFIED_ROBUST: 'Certified robust' }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST']));
  protected readonly sealText = computed<[string, string, string]>(() => ({
    Not: ['Not robust', 'DECISION REQUIRED'],
    Understated: ['Understated', 'WINNER HOLDS'],
    Robust: ['Robust', 'CERTIFIED'],
  }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST'] as unknown as [string, string, string]));
  protected readonly headline = computed(() => {
    const d = this.d(); if (!d) return '';
    return d.verdict?.narrative?.headline || `${d.acts.lifetime.winner} has the lowest 12-year cost, by ${cr(d.acts.lifetime.margin_cr)}.`;
  });
  protected mismatch(name: string): boolean {
    const a = this.d()?.acts.after; return !!a && a.change.toLowerCase().includes(name.toLowerCase());
  }
  protected readonly outcomes = computed(() => {
    const d = this.d(); if (!d) return [];
    const out = [
      { rule: 'The rate in words prevails over the figure', winner: d.acts.after?.winner ?? d.acts.lifetime.winner, why: d.acts.after ? `As the tender\u2019s own clause says. ${d.acts.after.change}.` : 'No conflicting figure found.' },
      { rule: 'The lower of the two readings is taken', winner: d.acts.lifetime.winner, why: `On its figure, ${d.acts.lifetime.winner} is ${cr(d.acts.lifetime.margin_cr)} cheaper over twelve years.` },
      { rule: 'The tender\u2019s year-one price metric is used', winner: d.acts.year_one_winner, why: 'Lowest aggregate payment in the first year, ignoring price adjustment' },
    ];
    return out;
  });

  protected readonly parts = [
    { t: 'TrueCost', path: 'truecost', icon: 'search', c: 'var(--tc)', d: 'Every extracted figure with its quote, page and source.' },
    { t: 'Engine', path: 'engine', icon: 'sliders', c: 'var(--ink)', d: 'The 12-year projection. Change any input and re-run it live.' },
    { t: 'RedSeal', path: 'redseal', icon: 'shield', c: 'var(--rs)', d: 'Each challenge, its evidence and the engine re-run.' },
    { t: 'Agent run', path: 'run', icon: 'play', c: 'var(--g-blue)', d: 'Replay what the Gemini agents did, step by step.' },
  ];
}
```

## `ui/src/app/pages/truecost.ts`
```ts
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap } from 'rxjs';
import { Api, BIDDER_COLOR, cr, inr } from '../core/api';
import { Icon } from '../shared/icon';
import { CaseHead } from './case-shell';

interface Ev { document?: string; page?: string; quote?: string }

@Component({
  selector: 'app-truecost',
  imports: [Icon, CaseHead],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<app-case-head [id]="id()" part="TrueCost" kicker="Part one · TrueCost" tone="var(--tc)"
  title="What each bid actually says"
  sub="Every figure the engine uses, extracted by Gemini with a verbatim quote and page, and every price index fetched from its official publisher."/>

@if (t(); as t) {
  <section class="wrap body">
    <div class="row bar">
      <div class="seg" role="tablist" aria-label="Bidder">
        @for (n of names(); track n) {
          <button type="button" role="tab" [class.on]="sel() === n" (click)="sel.set(n)">
            <i class="sw" [style.background]="color(n)"></i>{{ n }}
          </button>
        }
      </div>
      <span class="spacer"></span>
      <span class="pill tc"><app-icon name="sparkle" [size]="13"/> Extracted by Gemini · checked by code</span>
    </div>

    @if (sup(); as s) {
      <div class="cols">
        <!-- commercial terms -->
        <div class="blk">
          <h3 class="h2">Prices quoted</h3>
          @for (x of s.commercial?.terms ?? []; track x.term_id) {
            <article class="card card-b ev">
              <div class="row"><span class="overline">{{ x.kind.replace('_', ' ') }}</span><span class="spacer"></span><span class="src">{{ x.evidence.document }} \u00b7 p.{{ x.evidence.page }}</span></div>
              <div class="row"><div class="lbl">{{ x.label }}</div><span class="spacer"></span>
                @if (x.amount !== null && x.amount !== undefined) {
                  <span class="fig">{{ x.currency }} {{ x.amount }}</span><span class="muted small">{{ x.unit }}</span>
                }
              </div>
              @if (x.amount_in_words) { <div class="small" style="margin-top:4px">In words: <span class="mono">{{ x.amount_in_words }}</span></div> }
              @if (x.evidence.quote) { <blockquote><span class="quote">{{ x.evidence.quote }}</span></blockquote> }
            </article>
          }
        </div>

        <!-- escalation -->
        <div class="blk">
          <h3 class="h2">How the price moves</h3>
          @for (f of s.escalation?.formulae ?? []; track f.formula_id) {
            <article class="card card-b ev">
              <div class="formula mono">{{ f.formula_text }}</div>
              <div class="weights">
                <div class="wbar"><i class="fixed" [style.flex]="f.fixed_weight"></i>
                  @for (w of f.terms; track w.symbol; let i = $index) {
                    <i [style.flex]="w.weight" [style.opacity]="1 - i * 0.22"></i>
                  }
                </div>
                <div class="wl small"><span><b>fixed</b> {{ pct(f.fixed_weight) }}</span>
                  @for (w of f.terms; track w.symbol) { <span><b>{{ (w.weight * 100).toFixed(2) }}</b> {{ w.symbol }}</span> }
                </div>
              </div>
              <dl class="kv small">
                <dt>Adjusted every</dt><dd>{{ f.frequency_months }} months</dd>
                <dt>First revision</dt><dd>{{ f.first_adjustment || '-' }}</dd>
                <dt>Trigger</dt><dd>{{ f.trigger || '-' }}</dd>
                <dt>Base</dt><dd>{{ f.base_period || '-' }}</dd>
              </dl>
              @if (f.evidence?.quote) { <blockquote><span class="quote">{{ f.evidence.quote }}</span><span class="src">{{ f.evidence.document }} \u00b7 p.{{ f.evidence.page }}</span></blockquote> }
            </article>
          }

          <h3 class="h2 mt">Index sources</h3>
          <div class="card">
            @for (r of s.index_resolutions?.resolutions ?? []; track r.symbol) {
              <div class="ir">
                <span class="pill code">{{ r.symbol }}</span>
                <div class="irb small">
                  <div>{{ idx(r.series_key)?.label || r.series_key }}</div>
                  @if (r.url) { <a [href]="r.url" target="_blank" rel="noopener" class="src">{{ host(r.url) }}</a> }
                  @if (r.proxy) { <div class="muted">Proxy: {{ r.proxy }}</div> }
                </div>
                <span class="pill" [class.ok]="r.status === 'ok'" [class.warn]="r.status !== 'ok'">{{ r.step }}</span>
              </div>
            }
          </div>
        </div>
      </div>
    }

    <!-- open questions -->
    @if (questions().length) {
      <div class="blk">
        <h3 class="h2">What the agent could not decide alone</h3>
        <p class="small muted">TrueCost never guesses an award-critical value. It asks the buyer once, and the answer is stored and reused.</p>
        <div class="card">
          @for (q of questions(); track q.key) {
            <div class="q">
              <div class="small"><span class="mono muted">{{ q.key }}</span></div>
              <div class="lbl">{{ q.question }}</div>
              @if (answer(q.key); as a) { <div class="small ans"><app-icon name="check" [size]="13"/> {{ a }}</div> }
              @else if (q.suggestion) { <div class="small muted">Suggested: {{ q.suggestion }}</div> }
            </div>
          }
        </div>
      </div>
    }
  </section>
}
`,
styles: [`
  body { display: grid; gap: var(--s8); }
  .bar { flex-wrap: wrap; }
  .sw { width: 9px; height: 9px; border-radius: 3px; display: inline-block; margin-right: 8px; }
  .cols { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s8); align-content: start; }
  .blk { display: grid; gap: var(--s4); align-content: start; }
  .mt { margin-top: var(--s6); }
  .ev { display: grid; gap: 8px; }
  .lbl { font: 600 17px/1.35 var(--sans); color: var(--ink); }
  blockquote { margin: 0; padding-left: var(--s3); border-left: 2px solid var(--tc); display: grid; gap: 4px; }
  .formula { font-size: 14px; background: var(--paper-2); padding: 8px 12px; border-radius: var(--r1); }
  .weights { display: grid; gap: 6px; }
  .wbar { height: 8px; background: var(--rule); border-radius: 999px; display: flex; overflow: hidden; gap: 2px; }
  .wbar i { height: 100%; background: var(--tc); border-radius: 2px; } .wbar i.fixed { background: var(--ink-3); }
  .wl { display: flex; gap: var(--s4); color: var(--ink-3); } .wl b { color: var(--ink); }
  .kv { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; border-top: 1px solid var(--rule); padding-top: 8px; }
  .kv dt { color: var(--ink-3); } .kv dd { margin: 0; color: var(--ink); font-weight: 500; }
  .ir { display: grid; grid-template-columns: auto 1fr auto; gap: var(--s4); align-items: center; padding: 12px; border-bottom: 1px solid var(--rule); }
  .ir:last-child { border-bottom: 0; }
  .irb { display: grid; gap: 2px; min-width: 0; }
  .q { display: grid; gap: 6px; padding: 14px; border-bottom: 1px solid var(--rule); }
  .q:last-child { border-bottom: 0; }
  .ans { display: inline-flex; gap: 6px; align-items: center; color: var(--ok); font-weight: 500; }
  @media (max-width: 900px) { .cols { grid-template-columns: minmax(0, 1fr); } }
`] })
export class TrueCostPage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly t = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.truecost(id).pipe(catchError(() => of(null)))),
    { initialValue: null }
  ));
  protected readonly names = computed(() => Object.keys(this.t()?.suppliers ?? {}));
  protected readonly sel = signal<string>('');
  protected color(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }

  constructor() {
    toObservable(this.names).subscribe((ns) => { if (ns.length && !this.sel()) this.sel.set(ns[0]); });
  }

  protected readonly sup = computed(() => this.t()?.suppliers?.[this.sel()] ?? null);
  protected readonly questions = computed(() => {
    return (this.t()?.report?.questions_for_buyer ?? []).filter((q: { key: string }) => q.key.startsWith(this.sel()) || q.key.startsWith('rfq') || q.key.startsWith('index'));
  });
  protected answer(k: string): string { return this.t()?.answers?.[k] ?? ''; }
  protected idx(k: string) { return this.t()?.indices?.[k]; }
  protected colorN(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }
  protected pct(w: number) { return `${Math.round(w * 100)}%`; }
  protected host(u: string): string { try { return new URL(u).host; } catch { return u; } }
}
```

## `ui/src/app/pages/engine.ts`
```ts
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Subject, catchError, debounceTime, filter, firstValueFrom, of, switchMap, take } from 'rxjs';
import { Api, BIDDER_COLOR, WhatIf, cr } from '../core/api';
import { Chart, INK, axis, chartBase } from '../shared/chart';
import { Icon } from '../shared/icon';
import { CaseHead } from './case-shell';

interface Knobs { rates: Record<string, number>; discount: number; months: number; infl: Record<string, number> }
const INFL_MIN = -0.02, INFL_MAX = 0.08;
const INDEX_LABEL: Record<string, string> = { in_cpi_iw_all_india: 'CPI-IW (consumer prices)', in_wpi_all_commodities: 'WPI, all commodities', in_wpi_electricity: 'WPI, electricity' };

@Component({
  selector: 'app-engine',
  imports: [Chart, Icon, CaseHead],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<app-case-head [id]="id()" part="Engine" kicker="The deterministic engine" tone="var(--ink)"
  title="Twelve years, month by month"
  sub="Plain Python, no AI. It applies each bidder\u2019s own price-adjustment formula to projected indices, month by month, and discounts every payment to today. Change an input and it re-runs live."/>

@if (e(); as e) {
  <section class="wrap body">
    <div class="console card-dark">
      <div class="row ch"><span class="pill code"><app-icon name="code" [size]="12"/> engine.evaluate()</span>
        <span class="small">same inputs \u2192 same answer, every time</span>
        <span class="spacer"></span>
        @if (busy()) { <span class="small live">re-running…</span> }
        @if (dirty()) { <button class="btn btn-sm btn-ghost reset" type="button" (click)="reset()">Reset</button> }
      </div>
      <div class="sim">
        <div class="knobs">
          @for (n of names(); track n) {
            <label class="knob">
              <span class="row"><i class="sw" [style.background]="color(n)"></i> rate<span class="spacer"></span><b class="mono">{{ k().rates[n].toFixed(2) }}</b>/km</span>
              <input type="range" [min]="base().rates[n] * 0.9" [max]="base().rates[n] * 1.1" step="0.25" [value]="k().rates[n]" (input)="setRate(n, $any($event.target).valueAsNumber)" aria-label="n rate">
            </label>
          }
          <label class="knob">
            <span class="row">Discount rate<span class="spacer"></span><b class="mono">{{ (k().discount * 100).toFixed(1) }}%</b></span>
            <input type="range" min="0.04" max="0.16" step="0.005" [value]="k().discount" (input)="set('discount', $any($event.target).valueAsNumber)" aria-label="Discount rate">
          </label>
          <div class="infl-h"><span class="overline">Index inflation per year</span>
            @if (anyInfl()) { <button type="button" class="lnk" (click)="clearInfl()">Back to projected</button> }
          </div>
          @for (x of idx(); track x.k) {
            <div class="knob infl">
              <span class="row">{{ label(x.k) }}<span class="spacer"></span><b class="mono">{{ (val(x.k) * 100).toFixed(2) }}% / yr</b>@if (k().infl[x.k] !== undefined) { <span class="proj">projected</span> }</span>
              <div class="track" [class.has-tick]="!!inflFlip()[x.k]">
                <input type="range" [min]="inflMin" [max]="inflMax" step="0.0025" [value]="val(x.k)" (input)="setInfl(x.k, $any($event.target).valueAsNumber)">
                @if (inflFlip()[x.k]; as f) { <i class="tick" [style.left.%]="pos(f)"><span class="mono">flips \u2248 {{ (f * 100).toFixed(1) }}% a year (others projected)</span></i> }
              </div>
            </div>
          }
          <span class="hint">Each index starts at its own 3-year average. @for (x of idx(); track x.k) { @if (inflFlip()[x.k]; as f) { {{ baseWinner() }} keeps the award only while {{ label(x.k) }} stays {{ f > x.rate ? 'below' : 'above' }} = {{ (f * 100).toFixed(1) }}% a year (others projected). } }</span>
          <label class="knob">
            <span class="row">Contract length<span class="spacer"></span><b class="mono">{{ k().months }} months</b></span>
            <div class="seg dark">
              @for (m of [120, 144]; track m) { <button type="button" [class.on]="k().months === m" (click)="set('months', m)">{{ m / 12 }} years</button> }
            </div>
          </label>
        </div>

        <div class="res">
          <div class="overline">Winner on 12-year cost</div>
          <div class="win" [style.color]="color(award().winner)">{{ award().winner }}</div>
          <div class="small">by <b>{{ cr(award().margin_cr) }}</b> ({{ award().margin_pct.toFixed(2) }}%) over {{ award().runner_up }}</div>
          <ol class="rank">
            @for (r of award().ranking; track r[0]; let i = $index) {
              <li><span class="mono n">{{ i + 1 }}</span><i class="sw" [style.background]="color(r[0])"></i>{{ r[0] }}<span class="spacer"></span><span class="mono">{{ cr(r[1]) }}</span></li>
            }
          </ol>
          @if (flipped()) { <div class="flip"><app-icon name="alert" [size]="14"/> The winner changed from {{ baseWinner() }}.</div> }
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card card-b">
        <h3 class="h2">Payments per year</h3>
        <p class="small muted">Including price adjustment, before discounting. ₹ crore.</p>
        <app-chart [options]="yearly()" [height]="300"/>
      </div>
      <div class="card card-b">
        <h3 class="h2">How much each price has risen</h3>
        <p class="small muted">Price-adjustment factor applied to the quoted rate (1.00 = no change).</p>
        <app-chart [options]="factors()" [height]="300"/>
      </div>
    </div>

    <div class="card card-b">
      <h3 class="h2">Index projections</h3>
      <p class="small muted">Each index grows at its recent average year-on-year rate (company policy: mean of the last 3 years).</p>
      <div class="tscroll"><table class="dtable"><thead><tr>
        <th>Method</th><th class="num">Years/yr</th><th class="num">Projected growth / yr</th>
      </tr></thead>
      <tbody>@for (s of idx(); track s.k) {
        <tr><td class="mono">{{ s.k }}</td><td>{{ s.method }}</td><td class="num">{{ (s.rate * 100).toFixed(2) }}%@if (k().infl[s.k] !== undefined) { <span class="muted"> \u2192 {{ (k().infl[s.k] * 100).toFixed(2) }}%</span> }</td></tr>
      }</tbody></table></div>
    </div>
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">Loading the engine…</div></div>
}
`,
styles: [
  '.body { display: grid; gap: var(--s8); }',
  '.card-dark { border-radius: var(--r4); padding: var(--s6); }',
  '.ch { color: var(--console-ink-2); flex-wrap: wrap; }',
  '.reset { color: var(--console-ink); border-color: var(--console-line); }',
  '.sim { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: var(--s8); }',
  '.knobs { display: grid; gap: var(--s5); }',
  '.knob { display: grid; gap: 8px; color: var(--console-ink-2); font-size: 14px; }',
  '.knob b { color: var(--console-ink); }',
  'input[type=range] { width: 100%; accent-color: #8fa6ff; }',
  '.seg.dark { background: var(--console-2); border-color: var(--console-line); }',
  '.seg.dark button { color: var(--console-ink-2); } .seg.dark button.on { background: var(--console-ink); color: var(--console); }',
  '.sw { width: 9px; height: 9px; border-radius: 3px; display: inline-block; margin-right: 8px; }',
  '.res { background: var(--console-2); border: 1px solid var(--console-line); border-radius: var(--r3); padding: var(--s6); display: grid; gap: 8px; align-content: start; }',
  '.res .overline { color: var(--console-ink-2); }',
  '.win { font: 600 34px/1.05 var(--sans); letter-spacing: -0.02em; filter: brightness(1.6) saturate(.9); }',
  '.rank { list-style: none; margin: var(--s3) 0 0; padding: 0; display: grid; gap: 2px; }',
  '.rank li { display: flex; align-items: center; padding: 9px 0; border-top: 1px solid var(--console-line); color: var(--console-ink); font-size: 14px; }',
  '.n { width: 22px; color: var(--console-ink-2); }',
  '.flip { display: flex; gap: 6px; align-items: center; color: #ff9b85; font-size: 13.5px; margin-top: 6px; }',
  '.tscroll { overflow-x: auto; }',
  '.infl-h { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }',
  '.proj { font-size: 11px; color: var(--console-ink-2); margin-left: 8px; }',
  '.infl .track { position: relative; }',
  '.infl .track.has-tick { padding-bottom: 20px; }',
  '.infl .track input { position: relative; z-index: 1; margin: 0; }',
  '.tick { position: absolute; top: 18px; width: 2px; height: 9px; background: #ff9b85; transform: translateX(-1px); }',
  '.tick span { position: absolute; top: 9px; left: 50%; transform: translateX(-50%); white-space: nowrap; font-size: 11px; color: #ff9b85; font-style: normal; }',
  '.hint { font-size: 12.5px; line-height: 1.5; color: var(--console-ink-2); }',
  '.lnk { background: none; border: 0; padding: 0; color: #8fa6ff; font: inherit; cursor: pointer; text-decoration: underline; }',
  '.knob .row { flex-wrap: wrap; }',
  '@media (max-width: 560px) { .card-dark { padding: var(--s4); } .res { padding: var(--s4); } }',
  '@media (max-width: 900px) { .sim { grid-template-columns: minmax(0, 1fr); } }',
] })
export class EnginePage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly cr = cr;
  protected readonly e = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.engine(id).pipe(catchError(() => of(null)))),
    { initialValue: null }
  ));
  protected readonly names = computed(() => Object.keys(this.e()?.rates ?? {}));
  protected readonly base = computed<Knobs>(() => {
    const e = this.e();
    const rates: Record<string, number> = {};
    for (const [n, r] of Object.entries(e?.rates ?? {}) as Record<string, { value: number }>[]) rates[n] = r.value;
    return { rates, discount: e?.result?.discount?.annual ?? 0.12, months: e?.result?.months ?? 144, infl: {} };
  });
  private readonly edits = signal<Partial<Knobs> | null>(null);
  protected readonly k = computed<Knobs>(() => ({ ...this.base(), ...(this.edits() ?? {}), rates: { ...this.base().rates, ...(this.edits()?.rates ?? {}) }, infl: { ...(this.edits()?.infl ?? {}) } }));
  protected readonly dirty = computed(() => this.edits() !== null);
  protected readonly busy = signal(false);
  protected readonly live = signal<WhatIf | null>(null);
  protected readonly req = new Subject<Knobs>();
  protected readonly inflMin = INFL_MIN;
  protected readonly inflMax = INFL_MAX;
  protected readonly inflFlip = signal<Record<string, number>>({});

  constructor() {
    const sub = this.req.pipe(
      debounceTime(180),
      switchMap((k) => {
        this.busy.set(true);
        return this.api.evaluate(this.id(), this.overrides(k)).pipe(catchError(() => of(null)));
      })
    ).subscribe((r) => { this.busy.set(false); if (r) this.live.set(r); });
    inject(DestroyRef).onDestroy(() => sub.unsubscribe());
    toObservable(this.e).pipe(filter((e) => !!e), take(1)).subscribe(() => this.findInflFlip());
  }

  /** Per index (others projected, quoted rates): bisect the rate at which the baseline winner changes. */
  private async findInflFlip() {
    const win = this.basewinner();
    const at = async (s: string, g: number) => (await firstValueFrom(this.api.evaluate(this.id(), this.overrides({ ...this.base(), infl: { [s]: g } })).pipe(catchError(() => of(null))))?.award.winner;
    const out: Record<string, number> = {};
    await Promise.all(this.idx().map(async ({ k: s, rate }) => {
      for (const edge of [INFL_MIN, INFL_MAX]) { // search toward each end of the slider
        if ((await at(s, edge)) === win) continue;
        let ok = rate, bad = edge;
        for (let i = 0; i < 9; i++) { const m = (ok + bad) / 2; if ((await at(s, m)) === win) ok = m; else bad = m; }
        out[s] = (ok + bad) / 2; return;
      }
    }));
    this.inflFlip.set(out);
  }

  private overrides(k: Knobs): Record<string, unknown> {
    const rates = (this.e()?.rates ?? {}) as Record<string, { param: string }>;
    const o: Record<string, unknown> = { discount_rate: k.discount, horizon_months: k.months };
    for (const [n, v] of Object.entries(k.rates)) o[`${n}.${rates[n].param}`] = v;
    for (const [s, g] of Object.entries(k.infl)) o[`index:${s}`] = { method: 'fixed', rate: g };
    return o;
  }

  protected setRate(n: string, v: number) {
    this.edits.set({ ...(this.edits() ?? {}), rates: { ...this.k().rates, [n]: v } });
    this.req.next(this.k());
  }
  protected set(key: 'discount' | 'months', v: number) {
    this.edits.set({ ...(this.edits() ?? {}), [key]: v });
    this.req.next(this.k());
  }
  protected setInfl(s: string, v: number) {
    this.edits.set({ ...(this.edits() ?? {}), infl: { ...this.k().infl, [s]: v } });
    this.req.next(this.k());
  }
  protected clearInfl() {
    this.edits.set({ ...(this.edits() ?? {}), infl: {} });
    this.req.next(this.k());
  }
  protected val(s: string) { return this.k().infl[s] ?? this.idx().find((x) => x.k === s)?.rate ?? 0; }
  protected label(s: string) { return INDEX_LABEL[s] ?? s; }
  protected pos(g: number) { return (g - INFL_MIN) / (INFL_MAX - INFL_MIN) * 100; }
  protected readonly anyInfl = computed(() => Object.keys(this.k().infl).length > 0);
  protected reset() { this.edits.set(null); this.live.set(null); }

  protected readonly award = computed(() => this.live()?.award ?? this.e()!.result.award);
  protected readonly basewinner = computed(() => this.e()?.result.award.winner ?? '');
  protected readonly flipped = computed(() => !!this.live() && this.award().winner !== this.basewinner());
  protected color(n: string) { return BIDDER_COLOR[n] ?? INK.ink; }

  private yearlyData = computed<Record<string, Record<string, number>>>(() => {
    const l = this.live(); if (l) return l.yearly;
    const s = (this.e()?.result?.suppliers ?? {}) as Record<string, { yearly: Record<string, { tco_esc: number }> }>;
    return Object.fromEntries(Object.entries(s).map(([n, x]) => [n, Object.entries(x.yearly).map(([y, v]) => [y, v.tco_esc])]));
  });
  private factorData = computed<Record<string, Record<string, number>>>(() => {
    const l = this.live(); if (l) return l.factors;
    const s = (this.e()?.result?.suppliers ?? {}) as Record<string, { escalators: Record<string, { by_year: Record<string, number> }> }>;
    return Object.fromEntries(Object.entries(s).map(([n, x]) => [n, x.escalators[0]?.by_year ?? {}]));
  });

  protected readonly yearly = computed(() => {
    const d = this.yearlyData(); const ys = Object.keys(Object.values(d)[0] ?? {});
    return {
      ...chartBase(), grid: { left: 8, right: 8, top: 30, bottom: 4, containLabel: true },
      legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, textStyle: { color: INK.ink2 } },
      tooltip: { ...(chartBase()['tooltip'] as object), trigger: 'axis', valueFormatter: (v: number) => `\u20b9${v.toFixed(2)} cr` },
      xAxis: { type: 'category', data: ys, ...axis(), splitLine: { show: false } },
      yAxis: { type: 'value', ...axis() },
      series: Object.entries(d).map(([n, v]) => ({ name: n, type: 'bar', barGap: '10%', itemStyle: { color: this.color(n), borderRadius: [3, 3, 0, 0] }, data: ys.map((y) => +v[y] / 1e7).toFixed(2)) }),
    };
  });

  protected readonly factors = computed(() => {
    const d = this.factorData(); const ys = Object.keys(Object.values(d)[0] ?? {});
    return {
      ...chartBase(), grid: { left: 8, right: 8, top: 30, bottom: 4, containLabel: true },
      legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, textStyle: { color: INK.ink2 } },
      tooltip: { ...(chartBase()['tooltip'] as object), trigger: 'axis', valueFormatter: (v: number) => `\u20b9${v.toFixed(3)}` },
      xAxis: { type: 'category', data: ys, ...axis(), splitLine: { show: false } },
      yAxis: { type: 'value', min: 1, ...axis() },
      series: Object.entries(d).map(([n, v]) => ({ name: n, type: 'line', smooth: 0.3, symbol: 'none', lineStyle: { width: 2.5, color: this.color(n) }, itemStyle: { color: this.color(n) }, data: ys.map((y) => +v[y].toFixed(4)) })),
    };
  });

  protected readonly idx = computed(() => Object.entries((this.e()?.indices ?? {}) as Record<string, { method: string; years: number; rate: number }>).map(([k, s]) => ({ k, ...s })));
}
```

## `ui/src/app/pages/redseal.ts`
```ts
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap } from 'rxjs';
import { Api, BIDDER_COLOR, Challenge, ProofPack, cr } from '../core/api';
import { Icon } from '../shared/icon';
import { Seal } from '../shared/seal';
import { CaseHead } from './case-shell';

const KIND: Record<string, string> = {
  figure_vs_words: 'Figure vs words', discount_rate: 'Discount rate', index_window: 'Index window',
  contract_months: 'Contract length', award_metric: 'Award metric', combined: 'All buyer rules together',
};

@Component({
  selector: 'app-redseal',
  imports: [Icon, Seal, CaseHead],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<app-case-head [id]="id()" part="RedSeal" kicker="Part two · RedSeal" tone="var(--rs)"
  title="Trying to break the award"
  sub="RedSeal looks for anything that could change the winner. An objection only counts once the engine has re-run with the correction."/>

@if (p(); as p) {
  <section class="wrap body">
    <div class="card sum">
      <div class="sc">
        <span class="pill" [class.rs]="p.status === 'OVERTURNED'" [class.warn]="p.status === 'UNDERSTATED'" [class.ok]="p.status === 'CERTIFIED_ROBUST'">
          {{ p.status === 'OVERTURNED' ? 'Award not robust · decision required' : p.status === 'UNDERSTATED' ? 'Understated' : 'Certified robust' }}
        </span>
        <p class="lead">{{ p.narrative?.headline || p.summary }}</p>
        <div class="stats">
          <div><span class="overline">Challenges</span><b class="mono">{{ p.challenges.length }}</b></div>
          <div><span class="overline">Change the winner</span><b class="mono">{{ flips().length }}</b></div>
          <div><span class="overline">Original winner</span><b [style.color]="color(p.original_winner)">{{ p.original_winner }}</b></div>
        </div>
      </div>
      <app-seal [size]="150" [line1]="p.status === 'OVERTURNED' ? 'Not robust' : p.status === 'UNDERSTATED' ? 'Understated' : 'Robust'"
        [line2]="p.status === 'OVERTURNED' ? 'DECISION REQUIRED' : p.status === 'UNDERSTATED' ? 'WINNER HOLDS' : 'CERTIFIED'"
        [tone]="p.status === 'CERTIFIED_ROBUST' ? 'ok' : 'rs'"/>
    </div>

    <!-- ledger -->
    <div class="blk">
      <h2 class="h2">Challenge ledger</h2>
      <div class="ledger">
        @for (c of p.challenges; track c.challenge_id) {
          <article class="card ch" [class.open]="open() === c.challenge_id" [class.hot]="changes(c)">
            <button type="button" class="chh" (click)="toggle(c.challenge_id)" [attr.aria-expanded]="open() === c.challenge_id">
              <span class="pill" [class]="'pill ' + statusTone(c)">{{ statusLabel(c) }}</span>
              <span class="kt">{{ kind(c.kind) }}<span class="muted small"> · {{ c.supplier || 'all bidders' }}</span></span>
              <span class="spacer"></span>
              <span class="chg mono"><s>{{ c.original_value }}</s> → <b>{{ c.corrected_value }}</b></span>
              @if (c.rerun) { <span class="pill rs" [class.rs]="changes(c)">{{ c.rerun.winner → + c.rerun.winner : 'winner holds' }}</span> }
              <app-icon name="down" [size]="16"/>
            </button>
            @if (open() === c.challenge_id) {
              <div class="chb">
                <p>{{ c.reasoning }}</p>
                @if (c.evidence.length) {
                  <div class="evs"><span class="overline">Evidence</span>
                    @for (e of c.evidence; track $index) {
                      <blockquote><span class="quote">{{ e.quote }}</span><span class="src">{{ e.document }} · p. {{ e.page }}</span></blockquote>
                    }
                  </div>
                }
                @if (c.evidence_against.length) {
                  <div class="evs"><span class="overline">Evidence against</span>
                    @for (e of c.evidence_against; track $index) {
                      <blockquote class="ag"><span class="mono small">{{ e.quote }}</span><span class="src">{{ e.document }}</span></blockquote>
                    }
                  </div>
                }
                @if (c.rerun) {
                  <div class="rr"><span class="overline">Engine re-run · {{ c.rerun.label }}</span>
                    <div class="bars">
                      @for (r of c.rerun.ranking; track r[0]) {
                        <div class="br"><span class="bn"><i [style.background]="color(r[0])"></i>{{ r[0] }}</span>
                          <span class="track"><span class="fill" [style.width.%]="w(c.rerun, r[1])" [style.background]="color(r[0])"></span></span>
                          <span class="mono small">{{ cr(r[1]) }}</span>
                        </div>
                      }
                    </div>
                  </div>
                }
                @if (c.checks.length) { <div class="checks">@for (k of c.checks; track k) { <span class="pill code">{{ k }}</span> }</div> }
                @if (c.effect) { <p class="small muted">{{ c.effect }}</p> }
              </div>
            }
          </article>
        }
      </div>
    </div>

    <div class="grid-2">
      <div class="card card-b">
        <h3 class="h2">How far each price can move</h3>
        <p class="small muted">The rate at which each bidder would lose (or take) first place.</p>
        @for (f of p.flip_thresholds; track f.supplier) {
          <div class="ft">
            <div class="row"><span class="bn"><i [style.background]="color(f.supplier)"></i>{{ f.supplier }}</span>
              <span class="mono small">{{ f.current.toFixed(2) }} → {{ f.threshold.toFixed(2) }}</span>
              <span class="pill" [class.rs]="f.plausible" [class.mute]="!f.plausible">{{ f.change_pct > 0 ? '+' : '' }}{{ (f.change_pct * 100).toFixed(1) }}%</span>
            </div>
            <div class="bullet"><span class="zone" [style.width.%]="zone(f.change_pct)"></span><span class="mk" [style.left.%]="zone(f.change_pct)"></span></div>
            <div class="small muted">vs {{ f.against }}{{ f.plausible ? ' · within a plausible range' : '' }}</div>
          </div>
        }
      </div>
      <div class="card card-b">
        <h3 class="h2">Sensitivity</h3>
        <p class="small muted">Push each assumption to a low and a high value. Does the winner change?</p>
        <div class="tscroll"><table class="dtable"><thead><tr>
          <th>Assumption</th><th>Low → High</th><th>Winner</th>
        </tr></thead>
        <tbody>@for (s of p.sensitivity; track s.driver) {
          <tr><td>{{ s.driver }}</td><td class="mono small">{{ s.low_label }} → {{ s.high_label }}</td>
            <td>@if (s.flips) { <span class="pill rs">{{ s.winner_low }} → {{ s.winner_high }}</span> } @else { <span class="pill ok">{{ s.winner_low }} holds</span> }</td></tr>
        }</tbody></table></div>
      </div>
    </div>

    @if (p.narrative?.findings?.length) {
      <div class="card card-b">
        <h3 class="h2">Findings for the buyer</h3>
        <ol class="f1">@for (f of p.narrative!.findings; track $index) { <li>{{ f }}</li> }</ol>
        <p class="rec"><b>Recommendation.</b> {{ p.narrative!.recommendation }}</p>
      </div>
    }
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">Loading the proof pack…</div></div>
}
`,
styles: [
  '.body { display: grid; gap: var(--s8); }',
  '.sum { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--s8); padding: var(--s10) var(--s12); align-items: center; }',
  '.sc { display: grid; gap: var(--s4); align-content: start; max-width: 720px; }',
  '.stats { display: flex; gap: var(--s10); padding-top: var(--s5); border-top: 1px solid var(--rule); }',
  '.stats b { font: 600 22px/1 var(--sans); color: var(--ink); }',
  '.blk { display: grid; gap: var(--s4); }',
  '.ledger { display: grid; gap: var(--s3); }',
  '.ch.hot { border-color: var(--rs-100); box-shadow: 0 0 3px var(--rs-50); }',
  '.chh { width: 100%; display: flex; align-items: center; gap: var(--s3); background: transparent; border: 0; cursor: pointer; text-align: left; flex-wrap: wrap; }',
  '.chh app-icon { transition: transform var(--t-std) var(--ease); color: var(--ink-3); } .ch.open .chh app-icon { transform: rotate(180deg); }',
  '.kt { font-weight: 600; color: var(--ink); }',
  '.chg s { color: var(--ink-3); } .chg b { color: var(--ink); font-weight: 600; }',
  '.chb { padding: 0 var(--s5) var(--s5); display: grid; gap: var(--s4); border-top: 1px solid var(--rule); padding-top: var(--s4); }',
  '.evs { display: grid; gap: 6px; }',
  'blockquote { margin: 0; padding-left: var(--s3); border-left: 2px solid var(--h1); line-height: 1.9; white-space: pre-line; }',
  'blockquote.ag { border-left-color: var(--rule-2); }',
  '.rr { display: grid; gap: var(--s2); background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r2); padding: var(--s4); }',
  '.bars { display: grid; gap: 8px; }',
  '.br { display: grid; grid-template-columns: 120px 1fr auto; gap: var(--s3); align-items: center; }',
  '.track { height: 10px; background: var(--paper-2); border-radius: 5px; overflow: hidden; }.fill { display: block; height: 100%; border-radius: 5px; }',
  '.checks { display: flex; gap: 6px; flex-wrap: wrap; }',
  '.ft { display: grid; gap: 6px; padding: var(--s4) 0; border-bottom: 1px solid var(--rule); } .ft:last-child { border-bottom: 0; }',
  '.bullet { position: relative; height: 8px; background: var(--paper-2); border-radius: 4px; }',
  '.zone { position: absolute; left: 0; top: 0; bottom: 0; background: var(--rs-100); border-radius: 4px; }',
  '.mk { position: absolute; top: -4px; width: 3px; height: 16px; background: var(--rs); border-radius: 2px; transform: translateX(-1px); }',
  '.fl { margin: var(--s3) 0; padding-left: var(--s5); display: grid; gap: 8px; color: var(--ink-2); }',
  '.rec { padding: var(--s4); background: var(--rs-50); border: 1px solid var(--rs-2); color: var(--rs-700); }',
  '@media (max-width: 900px) { .sum { flex-direction: column-reverse; align-items: flex-start; } .br { grid-template-columns: 96px 1fr; } .br .mono { grid-column: 2; } }',
] })
export class RedSealPage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly cr = cr;
  protected readonly p = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.redseal(id).pipe(catchError(() => of(null)))),
    { initialValue: null }
  ));
  protected readonly open = signal<string | null>(null);
  protected readonly flips = computed(() => (this.p()?.challenges ?? []).filter((c) => !!c.rerun));

  protected toggle(id: string): void { this.open.set(this.open() === id ? null : id); }
  protected changes(c: Challenge): boolean { return !!c.rerun && c.rerun.winner !== this.p()?.original_winner; }
  protected kind(k: string): string { return KIND[k] ?? k.replace(/_/g, ' '); }
  protected statusTone(c: Challenge): string { return ({ verified: 'ok', contested: 'rs', rejected: 'mute', finding: 'warn' } as Record<string, string>)[c.status] ?? ''; }
  protected statusLabel(c: Challenge): string { return ({ verified: 'Verified', contested: 'Contested', rejected: 'Rejected', finding: 'Finding' } as Record<string, string>)[c.status] ?? c.status; }
  protected color(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }

  protected w(c: Challenge, v: number): number {
    const vs = c.rerun!.ranking.map((r) => r[1]);
    const lo = Math.min(...vs) * 0.9, hi = Math.max(...vs);
    return 20 + ((v - lo) / (hi - lo || 1)) * 80;
  }
  protected zone(pct: number) { return Math.min(100, Math.abs(pct) * 10); }
}
```

## `ui/DESIGN.md`
```markdown
# AwardShield Design System – "Evidence Desk"

## 0. Research Log
- Embedded refs: shortlisted `linear.app`, `stripe`, `claude` (editorial paper) -> picked Layer A `soft-skill` (premium, generous whitespace, nested surfaces, spring motion) + Layer B `linear.app` (precision, hairline borders, tight display tracking, mono for technical data). Linear's dark canvas is NOT taken; its precision is.
- Design council (4 sub-agents, parallel): Opus -> light "evidence desk" (paper, ink, highlighter, wax seal; self-annotating award document hero; "two pens on one page"); artistry -> forensic lightbox (dark, UV cyan / vermilion, serif display, story / executive toggle); visual-engineering -> obsidian (dark, buildable ECharts list: bullet, waterfall, heatmap, lazy charts); strategist -> sell defensible decisions, never "OVERTURNED" (contested) headline, plain words, replay run.
Decision: light evidence desk (Opus) + dark "engine console" band (one place, for deterministic code) + strategist's honest verdict language + visual-eng chart list.
- Old TrueCost "aurora glass" (dark, drifting indigo/violet/cyan blobs, glass cards) explicitly retired: 3 of 4 council members called it generic "AI demo"; blur and blobs wash out on projectors and recordings.
- Lazyweb / Imagen lanes: skipped (no image generation in this environment); the hero is built as SVG/CSS art instead.

## 1. Atmosphere & Identity
A procurement evidence desk under good light: warm paper, ink-black type, a cobalt pen that sources every number, a graphite ledger that computes, and a red wax seal that challenges. Calm, exact, audit-grade – the opposite of an AI toy.
**Signature:** The award document that marks itself up – TrueCost highlights in cobalt, the engine writes the 12-year total in the margin, RedSeal strikes the figure in red and presses the seal. Two pens, one page, one truth.
Colour IS meaning: cobalt = TrueCost (builds), red = RedSeal (challenges), graphite = engine (decides). Red is never a generic "bad" colour in this product.

## 2. Color

| Role | Token | Value | Usage |
|---|---|---|---|
| Canvas | `--paper` | `#F4F1EA` | page background (warm paper) |
| Canvas deep | `--paper-2` | `#ECE7DC` | alternating bands, insets |
| Sheet | `--sheet` | `#FFFFF8` | documents, cards (slightly warm white) |
| Ink | `--ink` | `#15171C` | primary text, engine identity |
| Ink 2 | `--ink-2` | `#3D424D` | body text |
| Ink 3 | `--ink-3` | `#6B7080` | captions, metadata (AA on paper: 4.9:1) |
| Rule | `--rule` | `#DDD6C8` | hairlines |
| Rule strong | `--rule-2` | `#C9C0AE` | input borders, table heads |
| TrueCost | `--tc` | `#2447D8` | cobalt pen: sources, extraction, links |
| TrueCost ramp | `--tc-50` / `-100` / `-700` | `#EEF2FF` / `#DCE4FF` / `#1A34A6` | tints, hover, pressed |
| RedSeal | `--rs` | `#C2361F` | sealing wax: challenges, strikes, verdict |
| RedSeal ramp | `--rs-50` / `-100` / `-700` | `#FDF0EC` / `#F8DAD2` / `#8E2414` | tints, seal shading |
| Highlighter | `--h1` | `#FFE58A` | verbatim quotes (text bg only) |
| Robust | `--ok` | `#1E7A4F` | CERTIFIED_ROBUST, "verified" check |
| Amber | `--warn` | `#B26A00` | "contested", "decision required" |
| Console bg | `--console` | `#0E1013` | the one dark band (engine) |
| Console line | `--console-line` | `rgba(255,255,255,.09)` | hairlines on console |
| Console text | `--console-ink` / `-2` | `#F2F0EA` / `#9DA3AE` | text on console |
| Google AI | `--g-blue/-red/-yellow/-green` | `#4285F4` / `#EA4335` / `#FBBC04` / `#34A853` | ONLY in the "Built with Google AI" strip |

Rules: accents are meaning, never decoration. Bidders get stable neutral-ish series colours in charts:
GreenMetro `#2F7D5B`, MetroLink `#2447D8`, UrbanDrive `#8A6F3E` (MetroLink = cobalt only coincidentally, so charts mark the WINNER with ink outline, not colour).

## 3. Typography
- Display: **Instrument Serif** (400, italic for emphasis) - legal-document gravitas for headlines only.
- UI / body: **Geist Variable** (400 / 500 / 600) - precise, not Inter.
- Mono: **Geist Mono Variable** - every number, quote, clause, id. Rule: if it came from a PDF or from code, it is mono.

| Level | Size | Weight | LH | Tracking | Usage |
|---|---|---|---|---|---|
| Hero | clamp(44px, 6.2vw, 92px) | Serif 400 | 0.98 | -0.02em | landing headline |
| Display | clamp(32px, 3.6vw, 52px) | Serif 400 | 1.05 | -0.015em | section titles |
| H1 | 28px | Geist 600 | 1.2 | -0.02em | page titles |
| H2 | 20px | Geist 600 | 1.3 | -0.01em | card titles |
| Lead | 19px | Geist 400 | 1.55 | -0.005em | hero sub, intros |
| Body | 15.5px | Geist 400 | 1.6 | 0 | default |
| Small | 13.5px | Geist 400 | 1.5 | 0 | secondary |
| Overline | 11.5px | Geist 600 | 1.3 | 0.12em upper | section labels |
| Figure | 15px | Mono 500 tnum | 1.4 | 0 | table numbers |
| Big figure | clamp(30px, 3.2vw, 44px) | Mono 500 tnum | 1.0 | -0.03em | KPIs |

## 4. Spacing & Layout
Base 4px: `--s1 4, --s2 8, --s3 12, --s4 16, --s5 20, --s6 24, --s8 32, --s10 40, --s12 48, --s16 64, --s20 80, --s24 96, --s32 128`.
Content max 1200px (`--wrap`), reading max 680px. Sections: `--s24` vertical (mobile `--s16`). Grid gutters `--s6`.
Radius: `--r1 6` (chips, inputs), `--r2 10` (buttons), `--r3 16` (cards), `--r4 24` (document sheet, bezels), pill 999.
Breakpoints: 640 / 900 / 1200. Below 900 every split becomes one column; no horizontal scroll at 375.

## 5. Components
- **Top bar**: floating pill (sheet, rule border, soft shadow), logo seal + wordmark, nav links, "Open the audit" button.
States: link hover ink underline; active route cobalt dot. Mobile: links collapse to a menu button.
- **Button**: `.btn` primary = ink fill, paper text, pill, trailing icon in its own circle (button-in-button);
`.btn-ghost` = transparent + rule border; `.btn-tc` cobalt; hover: icon circle translates 2px, press scale .98;
focus: 2px cobalt ring offset 2px; disabled .45 opacity.
- **Sheet** (double bezel): outer `--paper-2` tray 6px padding + rule, inner `--sheet` with inner highlight; radius `--r4`/`--r4-6`. Used for the hero document and key panels.
- **Card**: sheet bg, 1px rule, `--r3`, shadow-1; hover (if clickable) lift 2px + shadow-2.
- **Pen marks** (signature primitives): `.mark-tc` cobalt highlight sweep under text; `.strike-rs` red strike line drawn left->right; `.margin-note` handwritten-like note in mono with a leader line; `.seal` red wax SVG stamp.
- **Quote chip**: highlighter bg + mono text + "p.14 · BID_1" source tag; click -> evidence drawer.
- **Status pill**: verified (ok), contested (warn), rejected (ink-3 strike), finding (tc), AI (tc-50 bg), CODE (console).
- **Pipeline rail**: 5 nodes with AI / CODE / AI+PROOF badges, connectors animate a travelling dot.
- **Act stepper**: 3 tabs (Quoted rate / 12-year cost / After RedSeal) with sliding indicator; drives the acts chart.
- **Evidence drawer**: right slide-over (sheet), document name, page, quote with highlighter, source URL; Esc closes.
- **Data table**: hairline rows, mono right-aligned numbers, sticky head on paper-2.
- **Console band**: dark section with mono code lines + live numbers (engine).
- **Agent tree**: SVG/HTML tree of the ADK agents with Gemini badge per LLM agent, Python badge per code step.
Accessibility for all: visible focus, keyboard reachable, aria-labels on icon buttons, tabs with role=tablist.

## 6. Motion & Interaction
| Type | Duration | Easing | Usage |
|---|---|---|---|
| Micro | 140ms | cubic-bezier(.2,.8,.2,1) | hover, press |
| Standard | 260ms | cubic-bezier(.2,.8,.2,1) | tabs, drawer |
| Emphasis | 620ms | cubic-bezier(.16,1,.3,1) | reveals, chart morph |
| Seal | 520ms | cubic-bezier(.34,1.56,.64,1) | stamp press (scale 1.6 -> 1, rotate -12deg) |

Hero choreography (once, ~7s, replay button): 0.4s cobalt highlights sweep on rate + formula (TrueCost tags appear) ->
2.2s margin note writes "12-yr cost 549.02 cr · rank 1" -> 3.8s red strike through "63.00", note "words say Sixty Six"
-> 5.0s rank flips 1->2 -> 5.6s seal presses "NOT ROBUST". Only transform / opacity / clip-path / stroke-dashoffset.
Scroll reveals via IntersectionObserver (fade + 16px rise, 620ms).
`prefers-reduced-motion`: everything jumps to the final state, no loops.

## 7. Depth & Surface
Strategy: **mixed - paper tonal steps + soft warm shadows**, hairline rules. No glass, no blur on scrolling content.
| Level | Value | Usage |
|---|---|---|
| shadow-1 | `0 1px 2px rgba(40,30,10,.06), 0 1px 1px rgba(40,30,10,.04)` | cards at rest |
| shadow-2 | `0 6px 18px -6px rgba(40,30,10,.14), 0 2px 4px rgba(40,30,10,.05)` | hover, top bar |
| shadow-doc | `0 30px 60px -20px rgba(40,30,10,.25), 0 12px 24px -12px rgba(40,30,10,.12)` | hero document |

Paper grain: one fixed pointer-events-none SVG noise overlay at 3% opacity.

## 8. Accessibility Constraints & Accepted Debt
WCAG 2.2 AA: text >= 4.5:1 on paper (ink-3 `#6B7080` on `#F4F1EA` = 4.9:1), focus ring always visible, full keyboard, reduced motion respected, colour never the only signal (status pills carry icon + word; charts label values).
| Item | Location | Why accepted | Exit |
|---|---|---|---|
| No light/dark toggle | global | light evidence desk is the brand; console band covers dark | add if requested |
| Run page is a replay of a recorded run | `/case/:id/run` | judges must not wait 8 min; labelled "replay" | live runs via API later |