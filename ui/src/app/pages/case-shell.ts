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
  .tabs a { padding: 12px 14px; color: var(--ink-3); font: 500 14.5px/1 var(--sans); border-bottom: 2px solid transparent; margin-bottom: -1px; display: inline-flex; gap: 7px; align-items: center; white-space: nowrap; text-decoration: none !important; }
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
