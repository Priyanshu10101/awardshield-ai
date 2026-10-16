import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** The RedSeal wax seal (SVG, lit: radial wax gradient, rim, embossed ring text).
*/
@Component({
  selector: 'app-seal',
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
<svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 200 200"
role="img" [attr.aria-label]="line1() + ' ' + line2()">
  <defs>
    <radialGradient [attr.id]="id + 'w'" cx="38%" cy="32%" r="75%">
      <stop offset="0" stop-color="#E25A41"/><stop offset=".55" [attr.stop-color]="tone() === 'ok' ? '#2A8A5E' : '#C2361F'"/>
      <stop offset="1" [attr.stop-color]="tone() === 'ok' ? '#155C3B' : '#7E2012'"/>
    </radialGradient>
    <path [attr.id]="id + 'r'" d="M100,100 m-66,0 a66,66 0 1,1 132,0 a66,66 0 1,1 -132,0"/>
  </defs>
  <path d="M100 8c12 0 16 9 27 11s22-3 29 6 1 19 6 29 13 15 11 27-12 14-14 25 6
  21-3 29-19 2-29 7-15 13-27 13-16-9-27-11-22 3-29-6-1-19-6-29-13-15-11-27 12-14
  14-25-6-21 3-29 19-2 29-7 15-13 27-13z"
  [attr.fill]="'url(#' + id + 'w)'"/>
  <circle cx="100" cy="100" r="74" fill="none" stroke="rgba(255,255,255,.28)"
  stroke-width="1.5"/>
  <circle cx="100" cy="100" r="56" fill="none" stroke="rgba(0,0,0,.18)"
  stroke-width="1"/>
  <text font-family="Geist Mono Variable, monospace" font-size="11"
  letter-spacing="3.2" fill="rgba(255,255,255,.82)">
    <textPath [attr.href]="'#' + id + 'r'" startOffset="0">REDSEAL · VERIFIED BY THE ENGINE · REDSEAL · AUDIT ·</textPath>
  </text>
  <text x="100" y="97" text-anchor="middle" font-family="Instrument Serif, serif"
  font-size="25" fill="#FFF6EE">{{ line1() }}</text>
  <text x="100" y="121" text-anchor="middle" font-family="Geist Variable, sans-serif" font-weight="600" font-size="9.5" letter-spacing="0.8" fill="rgba(255,246,238,.9)">{{ line2() }}</text>
</svg>
`,
styles: [':host{display:inline-block;filter:drop-shadow(0 10px 14px rgba(120,30,10,.28))}']
})
export class Seal {
  readonly size = input(150);
  readonly line1 = input('Not robust');
  readonly line2 = input('DECISION REQUIRED');
  readonly tone = input<'rs' | 'ok'>('rs');
  protected readonly id = 's' + Math.random().toString(36).slice(2, 8);
}
