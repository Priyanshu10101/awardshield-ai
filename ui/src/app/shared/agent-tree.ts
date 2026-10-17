import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type AgentState = 'waiting' | 'running' | 'done';
type Node = { id: string; label: string; kind: 'gemini' | 'code'; note?: string };

/** The real ADK agent tree of AwardShield (mirrors truecost_ai/agent.py and redseal_ai/agent.py).
 *  `states` (agent name -> state) lights nodes up during a run replay; `show` limits it to one part. */
const PER_BIDDER: Omit<Node, 'id'>[] = [
  { label: 'Read the prices', kind: 'gemini', note: 'commercial' },
  { label: 'Read the price-rise formula', kind: 'gemini', note: 'escalation' },
  { label: 'Fetch inflation data', kind: 'gemini', note: 'index_resolver' },
  { label: 'Build the 12-year cost', kind: 'gemini', note: 'cost_model' },
  { label: 'Check every link', kind: 'code', note: 'finalizer' },
];

@Component({
  selector: 'app-agent-tree',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<div class="tree" [class.dark]="dark()">
  @if (show() !== 'redseal') {
    <section class="part tc">
      <header><span class="pname">TrueCost AI</span><span class="kind mono">ADK SequentialAgent · Gemini</span><span class="spacer"></span><span class="count small">{{ tcGemini() }} AI sub-agents · {{ bidders().length }} code steps</span></header>
      <div class="col">
        <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('volume_extractor', 'Read the tender', 'gemini', 'volume_extractor') }"/>
        <span class="arr" aria-hidden="true">↓</span>
        <div class="par">
          <div class="plabel mono">ParallelAgent · one branch per bidder, up to 5 at once (more run in waves)</div>
          <div class="lanes">
            <span class="hd bhd">Bidder</span>
            @for (s of perBidder; track s.label; let last = $last) {
              <span class="hd"></span>@if (!last) { <span></span> }
            }
            @for (b of bidders(); track b) {
              <span class="bidder">{{ b }}</span>
              @for (s of perBidder; track s.label; let last = $last) {
                <ng-container *ngTemplateOutlet="chip; context: { $implicit: n(s.note + '_' + key(b), s.label, s.kind, s.note) }"/>
                @if (!last) { <span class="arr sm" aria-hidden="true">→</span> }
              }
            }
          </div>
        </div>
        <span class="arr" aria-hidden="true">↓</span>
        <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('orchestrator', 'Write the report', 'gemini', 'orchestrator') }"/>
      </div>
    </section>
  }

  @if (show() === 'all') {
    <div class="link" aria-hidden="true"><span>cost_model.json</span></div>
    <section class="part eng">
      <header><span class="pname">Engine</span><span class="kind mono">plain Python · no AI</span><span class="spacer"></span><span class="count small">144 months · NPV · award</span></header>
      <p class="small engp">Applies each bidder's own price formula to official index projections, month by month, and discounts every payment. Same inputs, same answer.</p>
    </section>
    <div class="link" aria-hidden="true"><span>re-run for every challenge</span></div>
  }

  @if (show() !== 'truecost') {
    <section class="part rs">
      <header><span class="pname">RedSeal AI</span><span class="kind mono">ADK SequentialAgent · Gemini</span><span class="spacer"></span><span class="count small">3 AI sub-agents · 2 code steps</span></header>
      <div class="flow">
        <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('load_case', 'Load the award', 'code', 'load_case') }"/>
        <span class="arr" aria-hidden="true">→</span>
        <div class="par">
          <div class="plabel mono">ParallelAgent · two challengers at the same time</div>
          <div class="lane two">
            <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('extraction_challenger', 'Re-read every bid', 'gemini', 'extraction_challenger') }"/>
            <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('assumption_challenger', 'Challenge the rules', 'gemini', 'assumption_challenger') }"/>
          </div>
        </div>
        <span class="arr" aria-hidden="true">→</span>
        <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('prover', 'Prove it with the engine', 'code', 'prover') }"/>
        <span class="arr" aria-hidden="true">→</span>
        <ng-container *ngTemplateOutlet="chip; context: { $implicit: n('narrator', 'Explain the verdict', 'gemini', 'narrator') }"/>
      </div>
    </section>
  }
</div>

<ng-template #chip let-c>
  <div class="chip" [class.code]="c.kind === 'code'" [class.running]="state(c.id) === 'running'" [class.done]="state(c.id) === 'done'" [attr.title]="c.id">
    <span class="row1"><span class="dotst" aria-hidden="true"></span><span class="cname">{{ c.label }}</span></span>
    <span class="row2"><span class="badge">{{ c.kind === 'code' ? 'code' : 'sub-agent' }}</span>@if (c.note) { <span class="note mono">{{ c.note }}</span> }</span>
  </div>
</ng-template>
`,
  imports: [NgTemplateOutlet],
  styles: [`
    :host { display: block; }
    .tree { display: grid; gap: 0; }
    .part { border: 1px solid var(--rule); border-top-width: 3px; border-radius: var(--r3); background: var(--sheet); padding: var(--s5); display: grid; gap: var(--s4); min-width: 0; }
    .part.tc { border-top-color: var(--tc); } .part.rs { border-top-color: var(--rs); } .part.eng { border-top-color: var(--ink); background: var(--console); color: var(--console-ink-2); }
    header { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
    .pname { font: 600 17px/1.2 var(--sans); color: var(--ink); } .tc .pname { color: var(--tc-700); } .rs .pname { color: var(--rs-700); } .eng .pname { color: var(--console-ink); }
    .kind { font-size: 11.5px; color: var(--ink-3); } .eng .kind, .eng .count { color: var(--console-ink-2); }
    .count { color: var(--ink-3); } .spacer { flex: 1; }
    .engp { margin: 0; color: var(--console-ink-2); }
    .flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
    .arr { color: var(--ink-3); font-size: 15px; } .arr.sm { font-size: 12px; }
    .par { border: 1px dashed var(--rule-2); border-radius: var(--r2); padding: 10px; display: grid; gap: 8px; background: var(--paper); min-width: 0; flex: 1 1 520px; }
    .plabel { font-size: 11px; color: var(--ink-3); }
    .col { display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 0; }
    .col > .par { align-self: stretch; flex: none; }
    .lanes { display: grid; grid-template-columns: auto repeat(4, auto 14px) auto; justify-content: center; align-items: center; gap: 8px 6px; overflow-x: auto; }
    .hd { font-size: 10.5px; color: var(--ink-3); text-align: center; white-space: nowrap; }
    .lanes .arr.sm { text-align: center; }
    .lane { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
    .lane.two { gap: 8px; }
    .bidder { font: 600 12px/1 var(--sans); color: var(--ink-2); padding-right: 6px; }
    .chip { display: grid; gap: 4px; padding: 6px 9px; border-radius: 8px; border: 1px solid var(--tc-100); background: var(--tc-50); min-width: 0; transition: background 250ms, border-color 250ms, box-shadow 250ms; }
    .rs .chip { border-color: var(--rs-100); background: var(--rs-50); }
    .chip.code, .rs .chip.code { border-color: var(--console); background: var(--console); }
    .row1 { display: flex; align-items: center; gap: 6px; } .row2 { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .cname { font: 600 12.5px/1.25 var(--sans); color: var(--ink); white-space: nowrap; } .chip.code .cname { color: var(--console-ink); }
    .badge { font: 600 9.5px/1 var(--sans); letter-spacing: .06em; text-transform: uppercase; padding: 2px 5px; border-radius: 4px; background: var(--sheet); color: var(--tc-700); }
    .rs .badge { color: var(--rs-700); } .chip.code .badge, .rs .chip.code .badge { background: var(--console-2); color: var(--console-ink-2); }
    .note { font-size: 10px; color: var(--ink-3); }
    .bhd { text-align: left; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; } .chip.code .note { color: var(--console-ink-2); }
    .dotst { width: 7px; height: 7px; border-radius: 50%; background: var(--rule-2); flex: none; }
    .chip.running { box-shadow: 0 0 0 2px #8fa6ff; } .chip.running .dotst { background: #4a6cf7; animation: pulse 1.2s var(--ease) infinite; }
    .chip.done .dotst { background: var(--g-green); }
    .link { display: flex; justify-content: center; padding: 6px 0; position: relative; }
    .link::before { content: ''; position: absolute; top: 0; bottom: 0; left: 50%; border-left: 1.5px dashed var(--rule-2); }
    .link span { position: relative; background: var(--paper); padding: 2px 10px; font: 500 11px/1.4 var(--mono); color: var(--ink-3); border: 1px solid var(--rule); border-radius: 999px; }

    /* ---- dark: on the console band. AI sub-agents glow blue / red; code steps invert to paper ---- */
    .dark .part { background: var(--console-2); border-color: var(--console-line); }
    .dark .part.tc { border-top-color: #6f8bff; } .dark .part.rs { border-top-color: #ff8a6e; }
    .dark .part.eng { background: var(--console-ink); border-color: var(--console-ink); color: var(--ink-2); }
    .dark .pname { color: var(--console-ink); } .dark .tc .pname { color: #a9bbff; } .dark .rs .pname { color: #ffab96; } .dark .eng .pname { color: var(--ink); }
    .dark .kind, .dark .count { color: var(--console-ink-2); } .dark .eng .kind, .dark .eng .count { color: var(--ink-3); }
    .dark .engp { color: var(--ink-2); }
    .dark .par { background: rgba(255,255,255,.025); border-color: rgba(255,255,255,.16); }
    .dark .plabel, .dark .hd, .dark .arr { color: var(--console-ink-2); } .dark .bidder { color: var(--console-ink); }
    .dark .chip { background: rgba(70,100,240,.16); border-color: rgba(143,166,255,.32); }
    .dark .rs .chip { background: rgba(226,90,65,.14); border-color: rgba(255,155,133,.32); }
    .dark .cname { color: var(--console-ink); }
    .dark .badge { background: rgba(255,255,255,.07); color: #a9bbff; } .dark .rs .badge { color: #ffab96; }
    .dark .note { color: var(--console-ink-2); }
    .dark .chip.code, .dark .rs .chip.code { background: var(--console-ink); border-color: var(--console-ink); }
    .dark .chip.code .cname { color: var(--ink); } .dark .chip.code .note { color: var(--ink-3); }
    .dark .chip.code .badge, .dark .rs .chip.code .badge { background: var(--paper-2); color: var(--ink-2); }
    .dark .dotst { background: rgba(255,255,255,.22); } .dark .chip.code .dotst { background: var(--rule-2); }
    .dark .link::before { border-left-color: rgba(255,255,255,.18); }
    .dark .link span { background: var(--console); border-color: var(--console-line); color: var(--console-ink-2); }
    @media (max-width: 900px) {
      .lanes { display: flex; flex-wrap: wrap; justify-content: flex-start; } .lanes .hd, .lanes > span:empty { display: none; }
      .lanes .bidder { width: 100%; margin-top: 4px; } .lanes .arr.sm { display: none; }
    }
    @media (max-width: 640px) { .part { padding: var(--s4); } .flow .arr { display: none; } .par { flex-basis: 100%; } }
  `],
})
export class AgentTree {
  readonly states = input<Record<string, AgentState>>({});
  readonly show = input<'all' | 'truecost' | 'redseal'>('all');
  /** draw on the dark console band (home page) instead of paper */
  readonly dark = input(false);
  readonly bidders = input<string[]>(['GreenMetro', 'MetroLink', 'UrbanDrive']);
  protected readonly perBidder = PER_BIDDER;
  /** volume + 4 per bidder + orchestrator */
  protected readonly tcGemini = computed(() => 2 + 4 * this.bidders().length);
  protected n(id: string, label: string, kind: 'gemini' | 'code', note?: string): Node { return { id, label, kind, note }; }
  protected key(b: string): string { return b.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''); }
  protected state(id: string): AgentState | undefined { return this.states()[id]; }
}

