import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/** Inline stroke icons (Lucide paths, 24x24). */
const P: Record<string, string> = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  check: 'M20 6 9 17l-5-5',
  x: 'M18 6 6 18M6 6l12 12',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M13 8H8M13 12H8M13 16H8',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3',
  code: 'M16 18l6-6-6-8M8 6l-6 6 6 6',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  scale: 'M12 3v18M5 7l7-3 7 3M3 11c0 3.3 2 6 5 6s5-2.7 5-6M13 11c0 3.3 2 6 5 6s5-2.7 5-6',
  globe: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z',
  play: 'M6 4l14 8-14 8z',
  pause: 'M7 4h3v16H7zM14 4h3v16h-3z',
  replay: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5',
  alert: 'M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  link: 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  cpu: 'M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M15 2m-2 0H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zM9 11h6v6H9z',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 11V3M1 14h6M9 8h6M17 16h6',
  layers: 'M12 2 2 7l10 5 10-5M2 17l10 5 10-5M2 12l10 5 10-5',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z',
  menu: 'M4 6h16M4 12h16M4 18h16',
  book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5ZM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5',
  clock: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2',
  down: 'M6 9l6 6 6-6',
  hash: 'M4 9h16M4 15h16M10 3 8 21M16 3l-2 18',
};

@Component({
  selector: 'app-icon',
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" [attr.stroke-width]="stroke()"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path
  [attr.d]="d()"/></svg>`,
  styles: [':host{display:inline-flex;flex:none}'],
})
export class Icon {
  readonly name = input.required<string>();
  readonly size = input<number>(16);
  readonly stroke = input<number>(1.75);
  protected readonly d = computed(() => P[this.name()] ?? '');
}
