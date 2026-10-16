import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap } from 'rxjs';
import { Api, BIDDER_COLOR } from '../core/api';
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
  .body { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s8); }
  .bar { flex-wrap: wrap; } .bar .seg { max-width: 100%; overflow-x: auto; scrollbar-width: none; } .bar .seg button { white-space: nowrap; display: inline-flex; align-items: center; }
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
    switchMap((id) => this.api.truecost(id).pipe(catchError(() => of(null))))
  ), { initialValue: null });
  protected readonly names = computed(() => Object.keys(this.t()?.suppliers ?? {}));
  protected readonly sel = signal<string>('');
  protected color(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }

  constructor() {
    toObservable(this.names).subscribe((ns) => { if (ns.length && !this.sel()) this.sel.set(ns[0]); });
  }

  protected readonly sup = computed(() => this.t()?.suppliers?.[this.sel()] ?? null);
  protected readonly questions = computed(() => {
    const sel = this.sel().toLowerCase();
    return (this.t()?.report?.questions ?? this.t()?.questions ?? []).filter((q: { key: string }) => { const k = q.key.toLowerCase(); return k.startsWith(sel) || k.startsWith('rfq') || k.startsWith('index'); });
  });
  protected answer(k: string): string { return this.t()?.answers?.[k] ?? ''; }
  protected idx(k: string) { return this.t()?.indices?.[k]; }
  protected colorN(n: string) { return BIDDER_COLOR[n] ?? 'var(--ink)'; }
  protected pct(w: number) { return `${Math.round(w * 100)}%`; }
  protected host(u: string): string { try { return new URL(u).host; } catch { return u; } }
}
