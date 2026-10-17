import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, afterNextRender, inject, viewChild } from '@angular/core';
import { BrandState } from '../core/brand';
import { RouterLink } from '@angular/router';
import { CASE_ID } from '../core/api';
import { Icon } from '../shared/icon';
import { Reveal } from '../shared/reveal';
import { Seal } from '../shared/seal';
import { HeroDoc } from './hero-doc';
import { Hands } from '../shared/hands';
import { AgentTree } from '../shared/agent-tree';

@Component({
  selector: 'app-landing',
  imports: [RouterLink, Icon, Reveal, Seal, HeroDoc, Hands, AgentTree],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<section class="hero">
  <div #brandmark class="wrap brandmark rise" style="--i:0">
    <svg class="bm-logo" width="56" height="56" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28" fill="#C2361F"/><circle cx="32" cy="32" r="21" fill="none" stroke="#FDF0EC" stroke-width="2" stroke-dasharray="3 3"/><path d="M22 33l7 7 13-15" fill="none" stroke="#FFFDF8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <h1 class="bm-name">Award<em>Shield</em></h1>
  </div>
  <app-hands class="rise" style="--i:1"/>
  <div class="wrap hero-grid">
    <div class="copy">
      <span class="pill rise" style="--i:0"><i class="dot" style="color:var(--rs)"></i> AI audit for public tenders · Gemini & Google ADK</span>
      <h2 class="display big rise" style="--i:1">The cheapest bid<br>is not always the <em>cheapest.</em></h2>
      <p class="lead rise" style="--i:2">Tenders are awarded on the price on paper. But prices rise over the contract, and one misread figure can change the winner.</p>
      <div class="agents rise" style="--i:3">
        <div class="ag ag-tc"><i class="dot"></i><div><b>TrueCost AI: finds the real cost.</b> Reads every bid and its price-adjustment formula, fetches official inflation data, and calculates what each bid will really cost over the whole contract.</div></div>
        <div class="ag ag-rs"><i class="dot"></i><div><b>RedSeal AI: tries to prove TrueCost AI wrong.</b> Re-checks every figure, rule and assumption. No award is signed until it survives the attack.</div></div>
      </div>
      <p class="small muted rise" style="--i:4">The AI reads the documents. Code does every calculation.</p>
      <div class="row ctas rise" style="--i:5">
        <a class="btn" routerLink="/case/{{CASE_ID}}">See a real audit <span class="ico"><app-icon name="arrow"/></span></a>
      </div>
    </div>
    <app-hero-doc class="rise" style="--i:2"/>
  </div>
</section>

<!-- TWO PARTS -->
<section class="section band">
  <div class="wrap">
    <div class="sh center reveal" appReveal>
      <span class="overline">Two agents, two jobs</span>
      <h2 class="display">One builds the case. <em>One attacks it.</em></h2>
    </div>
    <div class="grid-2 parts">
      <a class="part tcp card hoverable reveal" appReveal routerLink="/case/{{CASE_ID}}/truecost">
        <div class="ph-h"><span class="pill tc"><i class="dot"></i> Part one</span><app-icon name="arrow" [size]="18"/></div>
        <h3 class="name serif">TrueCost AI</h3>
        <p class="lead">Reads the tender and every bid. Pulls rates, formulas and indices, each with a verbatim quote, a page number and a live government source.</p>
        <ul class="ticks">
          <li><app-icon name="check" [size]="15"/> AI sub-agents in parallel, one branch per bidder</li>
          <li><app-icon name="check" [size]="15"/> Price indices fetched and frozen with a hash</li>
          <li><app-icon name="check" [size]="15"/> Engine projects 144 months, discounted</li>
        </ul>
        <div class="eg mono"><span class="quote">&#34;0.64 + 0.12·CPI-IW + 0.14·WPI...&#34;</span><span class="src">BID_1 p.3</span></div>
      </a>

      <a class="part rsp card hoverable reveal" appReveal routerLink="/case/{{CASE_ID}}/redseal">
        <div class="ph-h"><span class="pill rs"><i class="dot"></i> Part two</span><app-icon name="arrow" [size]="18"/></div>
        <h3 class="name serif">RedSeal AI</h3>
        <p class="lead">An adversarial auditor. It hunts for anything that could change the winner, then lets the engine decide whether the objection actually matters.</p>
        <ul class="ticks">
          <li><app-icon name="check" [size]="15"/> Words vs figures, tender rules, terms</li>
          <li><app-icon name="check" [size]="15"/> Every challenge re-run, not argued</li>
          <li><app-icon name="check" [size]="15"/> How far each bid can move before the winner flips</li>
        </ul>
        <div class="seal-mini"><app-seal [size]="92"/></div>
      </a>
    </div>
  </div>
</section>

<!-- PIPELINE -->
<section class="section" id="how">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline">How it works</span>
      <h2 class="display">The AI builds the inputs. <em>Code decides.</em></h2>
      <p class="lead muted">Language models are good at reading messy documents and bad at arithmetic. So they never rank a bid. A deterministic engine does every sum.</p>
    </div>
    <ol class="rail reveal" appReveal>
      @for (s of steps; track s.t; let i = $index) {
        <li class="step" [class]="'step ' + s.k">
          <div class="badge"><app-icon [name]="s.icon" [size]="18"/></div>
          <div class="kind mono">{{ s.kind }}</div>
          <div class="t">{{ s.t }}</div>
          <p class="small muted">{{ s.d }}</p>
        </li>
      }
    </ol>
  </div>
</section>

<!-- GOOGLE STACK + AGENT TREE -->
<section class="section console stack" id="agents">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline" style="color:var(--console-ink-2)">Built with Google AI</span>
      <h2 class="display">A multi-agent system, <em>not a prompt.</em></h2>
      <p class="lead stacklead">2 root agents, TrueCost AI and RedSeal AI, with 17 AI sub-agents on Gemini, several running in parallel. Every number between them comes from the deterministic engine.</p>
    </div>
    <div class="treewrap reveal" appReveal><app-agent-tree [dark]="true"/></div>
    <p class="small treenote">The real tree from the code (truecost_ai/agent.py, redseal_ai/agent.py), shown for this Indian tender's 3 bidders. <a routerLink="/case/{{CASE_ID}}/run">Watch it run →</a></p>
  </div>
</section>

<!-- VERDICT RULES -->
<section class="section band">
  <div class="wrap">
    <div class="sh reveal" appReveal>
      <span class="overline">Three possible verdicts</span>
      <h2 class="display">RedSeal AI can only say <em>what the engine proves.</em></h2>
    </div>
    <div class="grid-3">
      @for (v of verdicts; track v.t; let i = $index) {
        <div class="card card-b verdict reveal" appReveal [class.cur]="v.cur">
          <span class="pill" [class]="'pill ' + v.tone"><i class="dot"></i> {{ v.t }}</span>
          <p>{{ v.d }}</p>
          @if (v.cur) { <span class="now small"><app-icon name="alert" [size]="14"/> This case</span> }
        </div>
      }
    </div>
  </div>
</section>

<!-- CTA -->
<section class="section">
  <div class="wrap">
    <div class="bezel reveal" appReveal><div class="core cta">
      <div>
        <h2 class="display">Open the audit.</h2>
        <p class="lead muted">Start with the decision. Then go as deep as you want: the evidence, the engine, the challenges, the agent run.</p>
      </div>
      <div class="row wrapr">
        <a class="btn" routerLink="/case/{{CASE_ID}}">Decision brief <span class="ico"><app-icon name="arrow"/></span></a>
        <a class="btn btn-ghost" routerLink="/case/{{CASE_ID}}/run">Watch the agents <span class="ico"><app-icon name="play"/></span></a>
      </div>
    </div></div>
  </div>
</section>
`,
styles: [`
  .hero { padding: var(--s6) 0 var(--s20); overflow: hidden; }
  .brandmark { display: flex; justify-content: center; align-items: center; gap: var(--s4); margin-bottom: 4px; }
  app-hands { margin: 0 0 var(--s5); padding-left: calc(56px + var(--s4)); }
  .bm-logo { filter: drop-shadow(0 10px 16px rgba(120, 30, 10, .25)); }
  .bm-name { font: 400 clamp(40px, 4.6vw, 64px)/1 var(--serif); letter-spacing: -0.025em; color: var(--ink); }
  .bm-name em { font-style: italic; color: var(--rs); }
  .hero-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); gap: var(--s16); align-items: start; }
  .copy { display: grid; gap: var(--s6); justify-items: start; }
  .big { font-size: clamp(38px, 4.6vw, 64px); line-height: .98; letter-spacing: -0.025em; }
  .tc { color: var(--tc); font-weight: 600; } .rs { color: var(--rs); font-weight: 600; }
  .ctas { flex-wrap: wrap; }
  .copy .lead { font-size: 17.5px; }
  .agents { display: grid; gap: var(--s3); }
  .ag { display: grid; grid-template-columns: 12px minmax(0, 1fr); gap: var(--s3); padding: var(--s3) var(--s4); background: var(--sheet); border: 1px solid var(--rule); border-left-width: 3px; border-radius: var(--r2); font-size: 15px; line-height: 1.5; color: var(--ink-2); }
  .ag b { color: var(--ink); font-weight: 600; } .ag .dot { margin-top: 8px; }
  .ag-tc { border-left-color: var(--tc); } .ag-tc .dot { color: var(--tc); } .ag-tc b { color: var(--tc-700); }
  .ag-rs { border-left-color: var(--rs); } .ag-rs .dot { color: var(--rs); } .ag-rs b { color: var(--rs-700); }
  .facts { display: flex; gap: var(--s10); margin: var(--s2) 0 0; padding-top: var(--s5); border-top: 1px solid var(--rule); }
  .facts dd { margin: 4px 0 0; color: var(--ink); font-weight: 500; }

  .sh { display: grid; gap: var(--s4); max-width: 720px; margin-bottom: var(--s12); }
  .sh.center { margin-left: auto; margin-right: auto; text-align: center; justify-items: center; }
  .more { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; }
  .rail { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: var(--s3); position: relative; }
  .rail::before { content: ''; position: absolute; left: 6%; right: 6%; top: 22px; border-top: 1.5px dashed var(--rule-2); z-index: 0; }
  .step { position: relative; z-index: 1; display: grid; gap: 6px; align-content: start; }
  .badge { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; background: var(--sheet); border: 1px solid var(--rule); color: var(--ink); box-shadow: var(--shadow-1); margin-bottom: 8px; }
  .step.ai .badge { background: var(--tc-50); border-color: var(--tc-100); color: var(--tc); }
  .step.code .badge { background: var(--console); border-color: var(--console); color: var(--console-ink); }
  .step.rsk .badge { background: var(--rs-50); border-color: var(--rs-100); color: var(--rs); }
  .step.out .badge { background: var(--ink); color: var(--paper); }
  .kind { font-size: 10.5px; letter-spacing: .1em; color: var(--ink-3); }
  .step .t { font: 600 16px/1.3 var(--sans); color: var(--ink); }

  .parts { gap: var(--s6); }
  .part { display: grid; gap: var(--s4); padding: var(--s8); color: inherit; text-decoration: none !important; position: relative; overflow: hidden; align-content: start; }
  .ph-h { display: flex; justify-content: space-between; align-items: center; color: var(--ink-3); }
  .name { font-size: 54px; line-height: 1; letter-spacing: -0.02em; color: var(--ink); }
  .tcp { border-top: 3px solid var(--tc); } .rsp { border-top: 3px solid var(--rs); }
  .ticks { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; font-size: 14.5px; }
  .ticks li { display: flex; gap: 8px; align-items: center; } .tcp .ticks app-icon { color: var(--tc); } .rsp .ticks app-icon { color: var(--rs); }
  .eg { margin-top: var(--s2); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .seal-mini { position: absolute; right: 22px; bottom: 18px; transform: rotate(-12deg); }

  .treenote { margin-top: var(--s4); color: var(--console-ink-2); } .treenote a { color: #8fa6ff; }
  .treewrap { margin-top: var(--s2); }
  .stacklead { color: var(--console-ink-2); }
  .verdict { display: grid; gap: var(--s3); align-content: start; }
  .verdict p { font-size: 15px; }
  .verdict.cur { border-color: var(--rs-100); box-shadow: 0 0 4px var(--rs-50); }
  .now { display: inline-flex; gap: 6px; align-items: center; color: var(--rs); font-weight: 600; }

  .stack { border-radius: var(--r4); margin: 0 var(--s4); }

  .cta { padding: var(--s12); display: flex; justify-content: space-between; align-items: center; gap: var(--s8); }
  .cta > div:first-child { display: grid; gap: var(--s3); max-width: 560px; }
  .wrapr { flex-wrap: wrap; }

  @media (max-width: 1000px) {
    .hero-grid { grid-template-columns: minmax(0, 1fr); gap: var(--s10); }
    .rail { grid-template-columns: minmax(0, 1fr); gap: var(--s5); }
    .rail::before { left: 22px; right: auto; top: 0; bottom: 0; border-top: 0; border-left: 1.5px dashed var(--rule-2); }
    .step { grid-template-columns: 44px minmax(0, 1fr); column-gap: var(--s4); align-items: center; }
    .badge { grid-row: span 3; margin: 0; }
    .cta { flex-direction: column; align-items: flex-start; padding: var(--s8); }
  }
  @media (max-width: 560px) {
    .hero { padding-top: var(--s8); } .brandmark { margin-bottom: var(--s8); } .bm-logo { width: 44px; height: 44px; } .brandmark { gap: var(--s3); } app-hands { padding-left: calc(44px + var(--s3)); } .facts { gap: var(--s6); grid-template-columns: minmax(0, 1fr); }
    .stack { margin: 0; border-radius: 0; } .name { font-size: 44px; } .part { padding: var(--s6); }
    .seal-mini { display: none; }
  }
`] })
export class Landing {
  private readonly brandmark = viewChild.required<ElementRef<HTMLElement>>('brandmark');

  constructor() {
    const brand = inject(BrandState);
    let io: IntersectionObserver | undefined;
    // the top bar hides its small logo while this big one is visible (it is shown again on scroll)
    afterNextRender(() => {
      if (typeof IntersectionObserver === 'undefined') return;
      io = new IntersectionObserver(([e]) => brand.heroBrandVisible.set(e.isIntersecting), { rootMargin: '-72px 0px 0px 0px' });
      io.observe(this.brandmark().nativeElement);
    });
    inject(DestroyRef).onDestroy(() => { io?.disconnect(); brand.heroBrandVisible.set(false); });
  }

  protected readonly CASE_ID = CASE_ID;
  protected readonly steps = [
    { k: 'in', kind: 'INPUT', icon: 'file', t: 'Tender & bids', d: 'PDFs exactly as the buyer received them.' },
    { k: 'ai', kind: 'AI · GEMINI', icon: 'search', t: 'TrueCost AI', d: 'Extracts every rate, formula and index, each quoted and sourced.' },
    { k: 'code', kind: 'CODE', icon: 'code', t: 'Engine', d: '144 months of escalation, discounted. Same inputs, same answer.' },
    { k: 'rsk', kind: 'AI + PROOF', icon: 'shield', t: 'RedSeal AI', d: 'Challenges the award. Only engine re-runs count as proof.' },
    { k: 'out', kind: 'OUTPUT', icon: 'scale', t: 'Verdict', d: 'Robust, understated or not robust, with a proof pack.' },
  ];
  protected readonly verdicts = [
    { t: 'Certified robust', tone: 'ok', cur: false, d: 'No verified challenge changes the winner, and no bid sits near its flip point.' },
    { t: 'Understated', tone: 'warn', cur: false, d: 'The winner holds, but the true cost or the margin is materially different from what was reported.' },
    { t: 'Not robust · decision required', tone: 'rs', cur: true, d: 'A credible reading of the tender changes the winner. The buyer must decide which reading applies.' },
  ];
}
