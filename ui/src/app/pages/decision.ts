import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, of, switchMap } from 'rxjs';
import { Api, BIDDER_COLOR, CaseOverview, cr } from '../core/api';
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
            <th class="num">Quoted-rate cost</th><th class="num">12-yr cost</th><th class="num">Year one</th><th class="num">Price \u00d7, final year</th>
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
  .body { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s12); }
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
  protected readonly cr = cr;
  readonly id = input.required<string>();
  protected readonly failed = computed(() => this.d() === undefined);
  protected readonly d = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.case(id).pipe(catchError(() => of(undefined as CaseOverview | null | undefined))))
  ), { initialValue: null as CaseOverview | null | undefined });
  protected color(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }
  protected readonly tone = computed(() => ({ OVERTURNED: 'rs', UNDERSTATED: 'warn', CERTIFIED_ROBUST: 'ok' }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST']));
  protected readonly statusLabel = computed(() => ({ OVERTURNED: 'Award not robust \u2013 decision required', UNDERSTATED: 'Understated', CERTIFIED_ROBUST: 'Certified robust' }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST']));
  protected readonly sealText = computed<[string, string]>(() => ({
    OVERTURNED: ['Not robust', 'DECISION REQUIRED'] as [string, string],
    UNDERSTATED: ['Understated', 'WINNER HOLDS'] as [string, string],
    CERTIFIED_ROBUST: ['Robust', 'CERTIFIED'] as [string, string],
  }[this.d()?.verdict?.status ?? 'CERTIFIED_ROBUST']));
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
