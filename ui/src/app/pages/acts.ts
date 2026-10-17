import { ChangeDetectionStrategy, Component, OnDestroy, computed, input, signal } from '@angular/core';
import { CaseOverview, BIDDER_COLOR } from '../core/api';
import { Chart, INK, axis, chartBase } from '../shared/chart';

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
  <app-chart [options]="options()" [height]="250"/>
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
    { k: 'After RedSeal AI', why: '\u201cGreenMetro\u2019s rate in words is \u201cSixty Six\u201d, not 63.00. The tender says words prevail. Re-run: MetroLink wins.' },
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
