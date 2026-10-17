import { ChangeDetectionStrategy, Component, DestroyRef, afterNextRender, computed, inject, signal } from '@angular/core';
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
    tab: 'TrueCost AI', who: 'tc',
    title: 'Over 12 years, GreenMetro is ₹13.6 cr cheaper.',
    metric: 'Real 12-year cost · ₹ crore, today\u2019s value',
    lo: 530, hi: 585,
    rows: [
      { name: 'GreenMetro', color: '#2F7D5B', value: 549.02, label: '₹549.02 cr', note: 'prices rise slowly' },
      { name: 'MetroLink', color: '#2447D8', value: 562.64, label: '₹562.64 cr', note: '70% tied to inflation' },
      { name: 'UrbanDrive', color: '#8A6F3E', value: 575.23, label: '₹575.23 cr' },
    ],
    explain: 'TrueCost AI reads every bid and its price-rise formula, fetches official inflation data, and adds up what each bid will really cost. The winner changes.',
  },
  {
    tab: 'RedSeal AI', who: 'rs',
    title: 'But GreenMetro\u2019s own bid says ₹66, not ₹63.',
    metric: 'Real 12-year cost, re-run with ₹66 · ₹ crore',
    lo: 530, hi: 585,
    rows: [
      { name: 'GreenMetro', color: '#2F7D5B', value: 575.17, label: '₹575.17 cr', note: 'at ₹66 / km' },
      { name: 'MetroLink', color: '#2447D8', value: 562.64, label: '₹562.64 cr' },
      { name: 'UrbanDrive', color: '#8A6F3E', value: 575.23, label: '₹575.23 cr' },
    ],
    explain: 'RedSeal AI tries to break the award. GreenMetro wrote ₹63.00 in figures but "Sixty Six" in words, and the Indian tender says words win. Re-run at ₹66: MetroLink wins.',
  },
];

const STEP_MS = 2000;
const TOUCH_HOLD_MS = 10000;

@Component({
  selector: 'app-hero-doc',
  imports: [Seal, Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<div class="stage" [attr.data-who]="s().who" (mouseenter)="hold(true)" (mouseleave)="hold(false)"
     (focusin)="hold(true)" (focusout)="hold(false)" (pointerdown)="touched($event)">
  <div class="sheet-shadow"></div>
  <article class="card" aria-label="An Indian e-bus tender in three steps">
    <div class="kicker">REAL PUBLIC TENDER 1376/CRUT · ODISHA, INDIA</div>
    <p class="about">The state transport body is hiring an operator to buy, run and maintain <b>200 electric buses</b> for <b>12 years</b>, paid per km driven. Three operators bid. Who should win?</p>

    <div class="tabrow">
    <div class="tabs" role="tablist">
      @for (st of stages; track st.tab; let i = $index) {
        @if (i > 0) { <app-icon class="sep" [class.lit]="i <= idx()" name="arrow" [size]="13" aria-hidden="true"/> }
        <button type="button" role="tab" class="tab" [class.next]="i === idx() + 1" [class.on]="i === idx()" [class.done]="i < idx()" [attr.aria-selected]="i === idx()" [attr.data-who]="st.who" (click)="go(i)">
          <span class="n">{{ i + 1 }}</span>{{ st.tab }}
        </button>
      }
    </div>
      <button type="button" class="pp" (click)="togglePlay()" [attr.aria-label]="stopped() ? 'Play the steps' : 'Pause the steps'"
              [attr.aria-pressed]="stopped()" [title]="stopped() ? 'Play' : 'Pause'">
        <app-icon [name]="stopped() ? 'play' : 'pause'" [size]="13"/>
      </button>
    </div>

    <h3 class="title">{{ s().title }}</h3>
    <div class="metric">{{ s().metric }}</div>

    <div class="board" [style.height.px]="rows().length * 52">
      @for (r of rows(); track r.name) {
        <div class="row" [style.transform]="'translateY(' + r.rank * 52 + 'px)'" [class.win]="r.rank === 0">
          <span class="nm"><i class="dot" [style.background]="r.color"></i>{{ r.name }}</span>
          <span class="track"><span class="bar" [style.width.%]="r.w" [style.background]="r.color"></span>
            @if (r.note) { <span class="note">{{ r.note }}</span> }</span>
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
    @if (idx() === 2) {
    <div class="answer"><b>AwardShield\u2019s answer:</b> the award is not safe. The committee must decide which price counts before signing.</div>
    }
    <div class="seal-slot" [class.in]="idx() === 2"><app-seal [size]="124"/></div>
  </article>

</div>
`,
styles: [`
  :host { display: block; overflow-x: clip; overflow-y: visible; }
  .stage { position: relative; padding: 14px 22px 8px 0; }
  .sheet-shadow { position: absolute; inset: 28px 40px 70px 20px; background: var(--paper-2); border: 1px solid var(--rule); border-radius: 18px; transform: rotate(-2.2deg); }
  .card { position: relative; background: var(--sheet); border: 1px solid var(--rule); border-radius: 18px; padding: 22px 26px 20px; box-shadow: var(--shadow-doc), inset 0 1px 0 #fff; min-height: 0; }
  .kicker { font: 600 10.5px/1.3 var(--mono); letter-spacing: .1em; color: var(--ink-3); padding-right: 90px; }
  .about { margin: 8px 0 0; font-size: 14px; line-height: 1.5; color: var(--ink-2); padding-right: 70px; } .about b { color: var(--ink); font-weight: 600; }
  .sep { color: var(--ink-4, #b9b4a8); flex: none; transition: color 300ms; } .sep.lit { color: var(--ink-2); }
  .tab.next { color: var(--ink-2); box-shadow: inset 0 0 1px var(--rule-2); }
  .tab.next:hover { background: var(--sheet); color: var(--ink); }
  .tabrow { display: flex; align-items: center; gap: 8px; margin: 14px 0 16px; }
  .pp { flex: none; width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--rule); background: var(--paper); color: var(--ink-2); display: grid; place-items: center; cursor: pointer; transition: background 200ms, color 200ms; }
  .pp:hover { background: var(--sheet); color: var(--ink); box-shadow: var(--shadow-1); }
  .pp[aria-pressed='true'] { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .tabs { min-width: 0; display: flex; align-items: center; gap: 4px; margin: 0; padding: 4px; background: var(--paper); border: 1px solid var(--rule); border-radius: 999px; width: fit-content; max-width: 100%; }
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
  .note { position: absolute; left: 0; top: 13px; line-height: 1; font: 500 11px/1 var(--sans); color: var(--ink-3); white-space: nowrap; }
  .val { font-size: 13.5px; text-align: right; color: var(--ink); }
  .badge { font: 600 11px/1 var(--sans); color: var(--ok); text-align: right; }
  .row.win .badge:not(:empty):before { content: '\\2713 '; }

  .evidence { margin-top: 10px; padding: 10px 12px; border: 1px dashed var(--rs-100); background: var(--rs-50); border-radius: 10px; display: grid; gap: 6px; animation: fade 450ms var(--ease-out); }
  .ev-1 { font: 600 10px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--rs-700); }
  .ev-row { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; font-size: 13px; }
  .struck { text-decoration: line-through; text-decoration-color: var(--rs); text-decoration-thickness: 2px; color: var(--ink-2); }
  .words { background: linear-gradient(transparent 55%, rgba(194,54,31,.22) 55%); padding: 0 3px; color: var(--ink); }
  .explain { margin: 14px 0 0; font-size: 14px; line-height: 1.55; color: var(--ink-2); min-height: 66px; animation: fade 450ms var(--ease-out); }
  .seal-slot { position: absolute; right: -30px; top: -42px; opacity: 0; transform: scale(1.7) rotate(-26deg); transition: opacity 260ms ease, transform 520ms var(--ease-seal); pointer-events: none; }
  .seal-slot.in { opacity: 1; transform: scale(1) rotate(-12deg); transition-delay: 600ms; }
  .answer { margin-top: 12px; padding: 10px 12px; border-radius: 10px; background: var(--rs-50); border: 1px solid var(--rs-100); font-size: 13.5px; line-height: 1.45; color: var(--ink); animation: fade 400ms var(--ease-out) 150ms both; }
  .answer b { color: var(--rs-700); }
  @keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  @media (max-width: 900px) {
    .stage { padding: 30px 0 4px; } .sheet-shadow { display: none; } .card { padding: 18px 16px; min-height: 0; }
    .seal-slot { right: -6px; top: -40px; } .seal-slot app-seal { width: 96px; } .title { font-size: 25px; }
  }
  @media (max-width: 520px) {
    .tab { padding: 6px 8px 6px 6px; font-size: 11.5px; gap: 5px; } .sep { display: none; } .tabs { gap: 2px; } .tab .n { width: 16px; height: 16px; }
    .about { padding-right: 0; font-size: 13.5px; }
    .row { grid-template-columns: 88px minmax(0, 1fr) 82px; gap: 8px; padding: 0 6px; } .badge { display: none; }
    .nm, .val { font-size: 12.5px; } .note { display: none; }
  }
  @media (max-width: 420px) { .tab .n { display: none; } .tab { padding: 6px 9px; } .pp { width: 30px; height: 30px; } }
  @media (max-width: 360px) { .tab { font-size: 10.5px; padding: 5px 6px 5px 5px; gap: 4px; } .tab .n { display: none; } }
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

  /** Autoplay: the three steps loop every STEP_MS; paused while the pointer (or keyboard focus) is on the
   *  card - someone is explaining it - and for a while after a tap on touch screens. Off for reduced motion. */
  private readonly paused = signal(false);
  /** The presenter's pause button: no autoplay until Play is pressed again. */
  protected readonly stopped = signal(false);
  private touchUntil = 0;
  constructor() {
    let timer: ReturnType<typeof setInterval> | undefined;
    afterNextRender(() => {
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      timer = setInterval(() => {
        if (!this.paused() && !this.stopped() && Date.now() > this.touchUntil) this.idx.set((this.idx() + 1) % STAGES.length);
      }, STEP_MS);
    });
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }
  protected hold(on: boolean): void { this.paused.set(on); }
  protected togglePlay(): void { this.stopped.update((v) => !v); }
  protected touched(e: PointerEvent): void { if (e.pointerType !== 'mouse') this.touchUntil = Date.now() + TOUCH_HOLD_MS; }
}
