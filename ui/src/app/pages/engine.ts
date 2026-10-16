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
              <span class="row"><i class="sw" [style.background]="color(n)"></i>{{ n }} rate<span class="spacer"></span><b class="mono">{{ k().rates[n].toFixed(2) }}</b>/km</span>
              <input type="range" [min]="base().rates[n] * 0.9" [max]="base().rates[n] * 1.1" step="0.25" [value]="k().rates[n]" (input)="setRate(n, $any($event.target).valueAsNumber)" [attr.aria-label]="n + ' rate'">
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
              <span class="row">{{ label(x.k) }}<span class="spacer"></span><b class="mono">{{ (val(x.k) * 100).toFixed(2) }}% / yr</b>@if (k().infl[x.k] === undefined) { <span class="proj">projected</span> }</span>
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
        <th>Index</th><th>Method</th><th class="num">Projected growth / yr</th>
      </tr></thead>
      <tbody>@for (s of idx(); track s.k) {
        <tr><td>{{ label(s.k) }}</td><td class="mono">{{ s.method }} {{ s.years }}</td><td class="num">{{ (s.rate * 100).toFixed(2) }}%@if (k().infl[s.k] !== undefined) { <span class="muted"> \u2192 {{ (k().infl[s.k] * 100).toFixed(2) }}%</span> }</td></tr>
      }</tbody></table></div>
    </div>
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">Loading the engine…</div></div>
}
`,
styles: [
  '.body { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s8); }',
  '.card-dark { border-radius: var(--r4); padding: var(--s6); }',
  '.ch { color: var(--console-ink-2); flex-wrap: wrap; }',
  '.reset { color: var(--console-ink); border-color: var(--console-line); }',
  '.sim { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: var(--s8); }',
  '.knobs { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s5); min-width: 0; }',
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
  '@media (max-width: 560px) { .card-dark { padding: var(--s4); } .res { padding: var(--s4); } .tick span { white-space: normal; width: 150px; text-align: center; } }',
  '@media (max-width: 900px) { .sim { grid-template-columns: minmax(0, 1fr); } }',
] })
export class EnginePage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly cr = cr;
  protected readonly e = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.engine(id).pipe(catchError(() => of(null))))
  ), { initialValue: null });
  protected readonly names = computed(() => Object.keys(this.e()?.rates ?? {}));
  protected readonly base = computed<Knobs>(() => {
    const e = this.e();
    const rates: Record<string, number> = {};
    for (const [n, r] of Object.entries((e?.rates ?? {}) as Record<string, { value: number }>)) rates[n] = r.value;
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
    const win = this.baseWinner();
    const at = async (s: string, g: number) => (await firstValueFrom(this.api.evaluate(this.id(), this.overrides({ ...this.base(), infl: { [s]: g } })).pipe(catchError(() => of(null)))))?.award.winner;
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

  protected readonly award = computed(() => this.live()?.award ?? this.e()!.award);
  protected readonly baseWinner = computed<string>(() => this.e()?.award?.winner ?? '');
  protected readonly flipped = computed(() => !!this.live() && this.award().winner !== this.baseWinner());
  protected color(n: string) { return BIDDER_COLOR[n] ?? INK.ink; }

  private yearlyData = computed<Record<string, Record<string, number>>>(() => {
    const l = this.live(); if (l) return l.yearly;
    const s = (this.e()?.result?.suppliers ?? {}) as Record<string, { yearly: Record<string, { tco_esc: number }> }>;
    return Object.fromEntries(Object.entries(s).map(([n, x]) => [n, Object.fromEntries(Object.entries(x.yearly).map(([y, v]) => [y, v.tco_esc]))]));
  });
  private factorData = computed<Record<string, Record<string, number>>>(() => {
    const l = this.live(); if (l) return l.factors;
    const s = (this.e()?.result?.suppliers ?? {}) as Record<string, { escalators: Record<string, { by_year: Record<string, number> }> }>;
    return Object.fromEntries(Object.entries(s).map(([n, x]) => [n, Object.values(x.escalators)[0]?.by_year ?? {}]));
  });

  protected readonly yearly = computed(() => {
    const d = this.yearlyData(); const ys = Object.keys(Object.values(d)[0] ?? {});
    return {
      ...chartBase(), grid: { left: 8, right: 8, top: 30, bottom: 4, containLabel: true },
      legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, textStyle: { color: INK.ink2 } },
      tooltip: { ...(chartBase()['tooltip'] as object), trigger: 'axis', valueFormatter: (v: number) => `\u20b9${v.toFixed(2)} cr` },
      xAxis: { type: 'category', data: ys, ...axis(), splitLine: { show: false } },
      yAxis: { type: 'value', ...axis() },
      series: Object.entries(d).map(([n, v]) => ({ name: n, type: 'bar', barGap: '10%', itemStyle: { color: this.color(n), borderRadius: [3, 3, 0, 0] }, data: ys.map((y) => +(v[y] / 1e7).toFixed(2)) })),
    };
  });

  protected readonly factors = computed(() => {
    const d = this.factorData(); const ys = Object.keys(Object.values(d)[0] ?? {});
    return {
      ...chartBase(), grid: { left: 8, right: 8, top: 30, bottom: 4, containLabel: true },
      legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, textStyle: { color: INK.ink2 } },
      tooltip: { ...(chartBase()['tooltip'] as object), trigger: 'axis', valueFormatter: (v: number) => `\u00d7${v.toFixed(3)}` },
      xAxis: { type: 'category', data: ys, ...axis(), splitLine: { show: false } },
      yAxis: { type: 'value', min: 1, ...axis() },
      series: Object.entries(d).map(([n, v]) => ({ name: n, type: 'line', smooth: 0.3, symbol: 'none', lineStyle: { width: 2.5, color: this.color(n) }, itemStyle: { color: this.color(n) }, data: ys.map((y) => +(v[y] ?? 1).toFixed(4)) })),
    };
  });

  protected readonly idx = computed(() => Object.entries((this.e()?.indices ?? {}) as Record<string, { method: string; years: number; rate: number }>).map(([k, s]) => ({ k, ...s })));
}
