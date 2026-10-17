import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { BrandState } from './core/brand';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Icon } from './shared/icon';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<a class="skip" href="#main">Skip to content</a>
<header class="topbar" role="banner">
  <nav class="bar" [class.nobrand]="brand.heroBrandVisible()" aria-label="Main">
    <a routerLink="/" class="brand" [class.hide]="brand.heroBrandVisible()" [attr.tabindex]="brand.heroBrandVisible() ? -1 : null" aria-label="AwardShield home">
      <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28" fill="#C2361F"/><circle cx="32" cy="32" r="21" fill="none" stroke="#FDF0EC" stroke-width="2" stroke-dasharray="3 3"/><path d="M22 33l7 7 13-15" fill="none" stroke="#FFFDF8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="word">Award<b>Shield</b></span>
    </a>
    <div class="links" [class.open]="menu()">
      <a routerLink="/" [routerLinkActiveOptions]="{exact:true}" routerLinkActive="on" (click)="menu.set(false)">Home</a>
      <a routerLink="/case/IN-CRUT-EBUS" [routerLinkActiveOptions]="{exact:true}" routerLinkActive="on" (click)="menu.set(false)">Decision</a>
      <a routerLink="/case/IN-CRUT-EBUS/truecost" routerLinkActive="on" (click)="menu.set(false)"><i class="d tc"></i>TrueCost AI</a>
      <a routerLink="/case/IN-CRUT-EBUS/engine" routerLinkActive="on" (click)="menu.set(false)"><i class="d ink"></i>Engine</a>
      <a routerLink="/case/IN-CRUT-EBUS/redseal" routerLinkActive="on" (click)="menu.set(false)"><i class="d rs"></i>RedSeal AI</a>
      <a routerLink="/case/IN-CRUT-EBUS/run" routerLinkActive="on" (click)="menu.set(false)">Agent run</a>
    </div>
    <a routerLink="/case/IN-CRUT-EBUS" class="btn btn-sm cta">Open the audit</a>
    <button class="menu" type="button" [attr.aria-expanded]="menu()" (click)="menu.set(!menu())"><app-icon name="menu" [size]="20"/></button>
  </nav>
</header>
<main id="main"><router-outlet/></main>
<footer class="foot">
  <div class="wrap row">
    <span class="small muted">AwardShield · TrueCost AI + RedSeal AI · built on Gemini and Google ADK</span>
    <span class="spacer"></span>
    <span class="small muted">The AI builds the inputs. Code decides.</span>
  </div>
</footer>
`,
styles: [`
  .skip { position: absolute; left: -9999px; } .skip:focus { left: 16px; top: 12px; z-index: 200; background: var(--ink); color: var(--paper); padding: 8px 14px; border-radius: 8px; }
  .topbar { position: sticky; top: 0; z-index: 50; padding: 14px var(--s4) 0; pointer-events: none; }
  .bar { pointer-events: auto; max-width: var(--wrap); margin: 0 auto; display: flex; align-items: center; gap: var(--s4); padding: 8px 8px 8px 18px; border-radius: 999px; background: rgba(255,253,248,.86); border: 1px solid var(--rule); box-shadow: var(--shadow-2); backdrop-filter: blur(14px) saturate(1.2); -webkit-backdrop-filter: blur(14px) saturate(1.2); }
  .brand { display: flex; align-items: center; gap: 10px; color: var(--ink); text-decoration: none !important; white-space: nowrap; overflow: hidden; max-width: 220px; transition: opacity var(--t-std) var(--ease), max-width var(--t-std) var(--ease), margin var(--t-std) var(--ease); }
  /* hidden: collapse to zero width (and cancel the flex gap) so the links move into its place */
  .brand.hide { opacity: 0; max-width: 0; margin-right: calc(-1 * var(--s4)); pointer-events: none; }
  .links { transition: margin var(--t-std) var(--ease); } .nobrand .links { margin-left: 0; }
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
  protected readonly brand = inject(BrandState);
}
