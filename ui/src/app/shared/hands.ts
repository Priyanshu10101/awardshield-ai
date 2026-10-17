import { ChangeDetectionStrategy, Component } from '@angular/core';

/** "TrueCost AI [clasped hands] RedSeal AI": AwardShield is the two AIs together.
 *  The handshake is the Lucide line icon (same family as every other icon here), split by hand:
 *  the left hand in TrueCost blue, the right hand in RedSeal red. On load the two hands slide
 *  together and clasp; the names fade in. Reduced motion: shown already clasped. */
@Component({
  selector: 'app-hands',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<span class="lock" role="img" aria-label="TrueCost AI and RedSeal AI, joined">
  <span class="n tcn" aria-hidden="true">TrueCost AI</span>
  <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <g class="l"><path d="M3 3 2 14l6.47 6.47a1 1 0 0 0 3-3"/><path d="M3 4h8"/></g>
    <g class="r"><path d="m11 17 2 2a1 1 0 1 0 3-3"/><path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4"/><path d="m21 3 1 11h-2"/></g>
  </svg>
  <span class="n rsn" aria-hidden="true">RedSeal AI</span>
</span>
`,
  styles: [`
    :host { display: flex; justify-content: center; }
    .lock { display: inline-flex; align-items: center; gap: 10px; font: 600 13.5px/1 var(--sans); letter-spacing: .01em; }
    .tcn { color: var(--tc); } .rsn { color: var(--rs); }
    svg { display: block; overflow: visible; }
    .l { stroke: var(--tc); } .r { stroke: var(--rs); }
    .l { animation: inL 900ms var(--ease-out) 500ms both; }
    .r { animation: inR 900ms var(--ease-out) 500ms both; }
    .n { animation: fade 600ms var(--ease-out) 1100ms both; }
    @keyframes inL { from { transform: translateX(-7px); opacity: 0; } to { transform: none; opacity: 1; } }
    @keyframes inR { from { transform: translateX(7px); opacity: 0; } to { transform: none; opacity: 1; } }
    @keyframes fade { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { .l, .r, .n { animation: none; } }
  `],
})
export class Hands {}
