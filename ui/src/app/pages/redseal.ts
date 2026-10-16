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
              @if (c.rerun) { <span class="pill" [class.rs]="changes(c)" [class.ok]="!changes(c)">{{ changes(c) ? '→ ' + c.rerun.winner : 'winner holds' }}</span> }
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
                          <span class="track"><span class="fill" [style.width.%]="w(c, r[1])" [style.background]="color(r[0])"></span></span>
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
              <span class="pill" [class.rs]="f.plausible" [class.mute]="!f.plausible">{{ f.change_pct > 0 ? '+' : '' }}{{ f.change_pct.toFixed(1) }}%</span>
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
        <ol class="fl">@for (f of p.narrative!.findings; track $index) { <li>{{ f }}</li> }</ol>
        <p class="rec"><b>Recommendation.</b> {{ p.narrative!.recommendation }}</p>
      </div>
    }
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">Loading the proof pack…</div></div>
}
`,
styles: [
  '.body { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--s8); }',
  '.sum { display: flex; justify-content: space-between; gap: var(--s8); padding: var(--s10) var(--s12); align-items: center; }',
  '.sc { min-width: 0; justify-items: start; display: grid; gap: var(--s4); align-content: start; max-width: 720px; }',
  '.stats { display: flex; flex-wrap: wrap; gap: var(--s4) var(--s10); padding-top: var(--s5); border-top: 1px solid var(--rule); }',
  '.stats > div { display: grid; gap: 6px; } .stats b { font: 600 22px/1 var(--sans); color: var(--ink); }',
  '.blk { display: grid; gap: var(--s4); }',
  '.ledger { display: grid; gap: var(--s3); }',
  '.ch.hot { border-color: var(--rs-100); box-shadow: 0 0 3px var(--rs-50); }',
  '.chh { padding: 14px var(--s5); width: 100%; display: flex; align-items: center; gap: var(--s3); background: transparent; border: 0; cursor: pointer; text-align: left; flex-wrap: wrap; }',
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
  '.tscroll { overflow-x: auto; }',
  '.checks { display: flex; gap: 6px; flex-wrap: wrap; } .checks .pill { white-space: normal; max-width: 100%; }',
  '.ft { display: grid; gap: 6px; padding: var(--s4) 0; border-bottom: 1px solid var(--rule); } .ft:last-child { border-bottom: 0; }',
  '.bullet { position: relative; height: 8px; background: var(--paper-2); border-radius: 4px; }',
  '.zone { position: absolute; left: 0; top: 0; bottom: 0; background: var(--rs-100); border-radius: 4px; }',
  '.mk { position: absolute; top: -4px; width: 3px; height: 16px; background: var(--rs); border-radius: 2px; transform: translateX(-1px); }',
  '.fl { margin: var(--s3) 0; padding-left: var(--s5); display: grid; gap: 8px; color: var(--ink-2); }',
  '.rec { padding: var(--s4); background: var(--rs-50); border: 1px solid var(--rs-100); border-radius: var(--r2); color: var(--rs-700); }',
  '@media (max-width: 900px) { .sum { flex-direction: column-reverse; align-items: flex-start; padding: var(--s6); } .sum .pill { white-space: normal; } .br { grid-template-columns: 96px 1fr; } .br .mono { grid-column: 2; } }',
] })
export class RedSealPage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly cr = cr;
  protected readonly p = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.redseal(id).pipe(catchError(() => of(null))))
  ), { initialValue: null });
  protected readonly open = signal<string | null>(null);
  protected readonly flips = computed(() => (this.p()?.challenges ?? []).filter((c) => this.changes(c)));

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
