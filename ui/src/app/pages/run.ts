import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap } from 'rxjs';
import { Api, RunEvent, RunRecord } from '../core/api';
import { Icon } from '../shared/icon';
import { AgentState, AgentTree } from '../shared/agent-tree';
import { CaseHead } from './case-shell';

/** Plays a whole recorded run in about this many seconds, whatever its real length. */
const REPLAY_S = 20;
const TICK_MS = 100;
const RUN_LABEL: Record<string, string> = {
  truecost: 'TrueCost AI · full run', truecost_answers: 'TrueCost AI · with buyer answers', redseal: 'RedSeal AI',
};
/** Steps that are plain Python (no model call). */
const CODE = /^(finalizer_|load_case|prover)/;

type AgentRow = { name: string; code: boolean; state: 'waiting' | 'running' | 'done'; events: number; doneAt?: number };

/** Time-coded replay of a recorded ADK run (truecost / truecost_answers / redseal), from api/cases/{id}/runs. */
@Component({
  selector: 'app-run',
  imports: [Icon, CaseHead, AgentTree],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<app-case-head [id]="id()" part="Agent run" kicker="Replay" tone="var(--g-blue)"
  title="What the agents did, step by step"
  sub="A time-coded recording of a real run: every Gemini agent, every tool call and every code step, replayed here in about twenty seconds."/>

@if (runs(); as rs) {
  <section class="wrap body">
    @if (names().length) {
      <div class="row bar">
        <div class="seg" role="tablist" aria-label="Recorded runs">
          @for (n of names(); track n) {
            <button type="button" role="tab" [class.on]="sel() === n" [attr.aria-selected]="sel() === n" (click)="pick(n)">{{ label(n) }}</button>
          }
        </div>
        <span class="spacer"></span>
        @if (rec(); as r) {
          <span class="small muted"><app-icon name="clock" [size]="13"/> {{ r.started_at.replace('T', ' ').replace('+00:00', ' UTC') }} · {{ dur(r.duration_s) }} · {{ r.events.length }} events</span>
        }
      </div>

      @if (rec(); as r) {
        <div class="card card-b treecard">
          <div class="row th"><span class="overline">The agent tree</span><span class="spacer"></span><span class="small muted">lights up as the replay reaches each agent</span></div>
          <app-agent-tree [states]="treeStates()" [show]="sel() === 'redseal' || (!sel() && names()[0] === 'redseal') ? 'redseal' : 'truecost'" [bidders]="r.bidders ?? bidderNames"/>
        </div>
        <div class="console player">
          <div class="row ctl">
            <button class="btn btn-sm play" type="button" (click)="toggle()" [attr.aria-label]="playing() ? 'Pause' : 'Play'">
              <app-icon [name]="playing() ? 'pause' : 'play'" [size]="14"/> {{ playing() ? 'Pause' : (clock() >= r.duration_s ? 'Done' : 'Play') }}
            </button>
            <button class="btn btn-sm btn-ghost again" type="button" (click)="restart()"><app-icon name="replay" [size]="14"/> From the start</button>
            <span class="spacer"></span>
            <span class="mono t">{{ dur(clock()) }} / {{ dur(r.duration_s) }}</span>
          </div>
          <div class="prog" aria-hidden="true"><span [style.width.%]="progress()"></span>
            @for (m of marks(); track $index) { <i [style.left.%]="m"></i> }
          </div>

          <div class="cols">
            <ol class="agents" aria-label="Agents">
              @for (a of agents(); track a.name) {
                <li [class]="a.state">
                  <span class="st" aria-hidden="true"></span>
                  <span class="nm mono">{{ a.name }}</span>
                  <span class="pill code kind">{{ a.code ? 'code' : 'Gemini' }}</span>
                  <span class="spacer"></span>
                  <span class="mono small n">{{ a.state === 'done' ? dur(a.doneAt ?? 0) : a.state === 'running' ? 'running' : '' }}</span>
                </li>
              }
            </ol>

            <div class="feed" aria-live="polite">
              @for (e of feed(); track $index) {
                <div class="ev" [class]="'ev ' + e.kind">
                  <span class="mono tm">{{ dur(e.t) }}</span>
                  <span class="who mono">{{ e.agent }}</span>
                  <span class="what">
                    @if (e.kind === 'call') { <b>calls {{ e.name }}</b> }
                    @else if (e.kind === 'result') { <b>{{ e.name }} returned</b> }
                    @else { <b>done</b> }
                    @if (e.detail) { <span class="mono det">{{ e.detail }}</span> }
                  </span>
                </div>
              } @empty {
                <div class="small idle">Press Play to replay the run.</div>
              }
            </div>
          </div>
        </div>
        <p class="small muted note">This is a replay of a recorded run (written by the runners to output/{{ id() }}/runs/), so nobody has to wait for the real one.
          Steps marked <b>code</b> are plain Python: the finalizers' link checks, the engine and RedSeal AI's prover never call a model.</p>
      }
    } @else {
      <div class="card card-b small muted">No recorded run yet. Run <span class="mono">python -m truecost_ai.runner {{ id() }}</span> or <span class="mono">python -m redseal_ai.runner {{ id() }}</span> to record one.</div>
    }
  </section>
} @else {
  <div class="wrap body"><div class="card card-b small muted">Loading the recorded runs…</div></div>
}
`,
  styles: [
    '.body { display: grid; gap: var(--s6); }',
    '.bar { flex-wrap: wrap; } .bar .small { display: inline-flex; gap: 6px; align-items: center; }',
    '.player { border-radius: var(--r4); padding: var(--s6); display: grid; gap: var(--s4); }',
    '.ctl { flex-wrap: wrap; } .t { color: var(--console-ink); font-size: 14px; }',
    '.play { background: var(--console-ink); color: var(--console); border-color: var(--console-ink); padding: 7px 14px; gap: 8px; }',
    '.again { color: var(--console-ink); border-color: var(--console-line); padding: 7px 14px; gap: 8px; }',
    '.prog { position: relative; height: 6px; background: var(--console-2); border-radius: 3px; }',
    '.prog span { position: absolute; left: 0; top: 0; bottom: 0; background: #8fa6ff; border-radius: 3px; transition: width 100ms linear; }',
    '.prog i { position: absolute; top: -3px; width: 2px; height: 12px; background: rgba(255,255,255,.25); }',
    '.cols { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.3fr); gap: var(--s6); }',
    '.agents { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; align-content: start; }',
    '.agents li { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--r1); color: var(--console-ink-2); font-size: 13px; transition: background var(--t-std) var(--ease), color var(--t-std) var(--ease); }',
    '.agents li.running { background: var(--console-2); color: var(--console-ink); }',
    '.agents li.done { color: var(--console-ink); }',
    '.st { width: 8px; height: 8px; border-radius: 50%; background: var(--console-line); flex: none; }',
    'li.running .st { background: #8fa6ff; animation: pulse 1.2s var(--ease) infinite; } li.done .st { background: var(--g-green); }',
    '.nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }',
    '.kind { font-size: 10.5px; padding: 1px 7px; background: var(--console-2); border-color: var(--console-line); }',
    '.n { color: var(--console-ink-2); }',
    '.feed { display: grid; gap: 2px; align-content: start; max-height: 460px; overflow-y: auto; scrollbar-width: thin; }',
    '.ev { display: grid; grid-template-columns: 52px minmax(0, 150px) minmax(0, 1fr); gap: 10px; padding: 7px 8px; border-radius: var(--r1); font-size: 13px; color: var(--console-ink-2); animation: rise 300ms var(--ease-out) both; }',
    '.ev.done { color: var(--console-ink); } .ev.done b { color: #7fd1a3; } .ev.call b { color: #8fa6ff; } .ev.result b { color: #f0c674; }',
    '.tm { color: var(--console-ink-2); } .who { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--console-ink); }',
    '.what { display: grid; gap: 2px; min-width: 0; } .det { font-size: 11.5px; color: var(--console-ink-2); overflow-wrap: anywhere; }',
    '.idle { color: var(--console-ink-2); padding: var(--s4); }',
    '.note { max-width: 860px; }',
    '.treecard { display: grid; gap: var(--s4); } .th { flex-wrap: wrap; }',
    '@media (max-width: 900px) { .cols { grid-template-columns: minmax(0, 1fr); } .ev { grid-template-columns: 48px minmax(0, 1fr); } .ev .who { grid-column: 2; } .ev .what { grid-column: 2; } }',
    '@media (max-width: 560px) { .player { padding: var(--s4); } }',
  ],
})
export class RunPage {
  private api = inject(Api);
  readonly id = input.required<string>();
  protected readonly runs = toSignal(toObservable(this.id).pipe(
    switchMap((id) => this.api.runs(id).pipe(catchError(() => of({} as Record<string, RunRecord>))))
  ), { initialValue: null });
  /** Runs in pipeline order. */
  protected readonly names = computed(() => {
    const order = ['truecost', 'truecost_answers', 'redseal'];
    const at = (n: string) => (order.indexOf(n) < 0 ? order.length : order.indexOf(n));
    return Object.keys(this.runs() ?? {}).sort((a, b) => at(a) - at(b) || a.localeCompare(b));
  });
  protected readonly sel = signal('');
  protected readonly rec = computed<RunRecord | null>(() => this.runs()?.[this.sel() || this.names()[0]] ?? null);
  protected readonly clock = signal(0);
  protected readonly playing = signal(false);
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.stop());
  }

  protected readonly progress = computed(() => {
    const r = this.rec(); return r && r.duration_s ? Math.min(100, (this.clock() / r.duration_s) * 100) : 0;
  });
  /** Where each agent finished, as ticks on the progress bar. */
  protected readonly marks = computed(() => {
    const r = this.rec(); if (!r || !r.duration_s) return [];
    return r.events.filter((e) => e.kind === 'done').map((e) => (e.t / r.duration_s) * 100);
  });
  protected readonly shown = computed<RunEvent[]>(() => (this.rec()?.events ?? []).filter((e) => e.t <= this.clock() && this.started()));
  /** Newest first, so the latest step is always visible. */
  protected readonly feed = computed(() => [...this.shown()].reverse().slice(0, 80));
  private readonly started = signal(false);

  protected readonly bidderNames = ['GreenMetro', 'MetroLink', 'UrbanDrive'];
  /** agent name -> replay state, for the tree */
  protected readonly treeStates = computed<Record<string, AgentState>>(() =>
    Object.fromEntries(this.agents().map((a) => [a.name, a.state])));

  protected readonly agents = computed<AgentRow[]>(() => {
    const r = this.rec(); if (!r) return [];
    const rows = new Map<string, AgentRow>();
    for (const e of r.events) {  // every agent, in order of first appearance
      if (!rows.has(e.agent)) rows.set(e.agent, { name: e.agent, code: CODE.test(e.agent), state: 'waiting', events: 0 });
    }
    for (const e of this.shown()) {
      const a = rows.get(e.agent)!;
      a.events++;
      if (e.kind === 'done') { a.state = 'done'; a.doneAt = e.t; } else if (a.state !== 'done') a.state = 'running';
    }
    return [...rows.values()];
  });

  protected label(n: string): string { return RUN_LABEL[n] ?? n.replace(/_/g, ' '); }
  protected dur(s: number): string {
    const m = Math.floor(s / 60), x = Math.floor(s % 60);
    return m ? `${m}m ${String(x).padStart(2, '0')}s` : `${s.toFixed(s < 10 ? 1 : 0)}s`;
  }

  protected pick(n: string): void { this.stop(); this.sel.set(n); this.clock.set(0); this.started.set(false); }
  protected toggle(): void {
    const r = this.rec(); if (!r) return;
    if (this.playing()) { this.stop(); return; }
    if (this.clock() >= r.duration_s) this.clock.set(0);
    this.started.set(true);
    this.playing.set(true);
    const step = (r.duration_s / REPLAY_S) * (TICK_MS / 1000);
    this.timer = setInterval(() => {
      const t = Math.min(r.duration_s, this.clock() + step);
      this.clock.set(t);
      if (t >= r.duration_s) this.stop();
    }, TICK_MS);
  }
  protected restart(): void { this.stop(); this.clock.set(0); this.started.set(false); this.toggle(); }
  private stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.playing.set(false);
  }
}
