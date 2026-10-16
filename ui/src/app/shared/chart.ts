import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, input,
signal, untracked } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { ECharts, EChartsCoreOption } from 'echarts/core';

/**
 * One ECharts canvas. The first non-empty option initialises the chart; later
 * options are merged with
 * `replaceMerge: ['series']` so same-named series morph (bars grow, lines redraw)
 * instead of being rebuilt.
 */
@Component({
  selector: 'app-chart',
  imports: [NgxEchartsDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div echarts class="ec" [options]="initial()" [style.height]="height() + 'px'"
  [initOpts]="{ renderer: 'canvas' }" [autoResize]="true" (chartInit)="onInit($event)"></div>`,
  styles: [':host{display:block;min-width:0} .ec{width:100%;min-height:120px}']
})
export class Chart {
  readonly options = input.required<EChartsCoreOption>();
  /** px; 0 = fill the host's height */
  readonly height = input<number>(300);
  protected readonly initial = signal<EChartsCoreOption>({});
  private chart: ECharts | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => (this.chart = null));
    effect(() => {
      const o = this.options();
      if (!o || !Object.keys(o).length) return;
      untracked(() => {
        const opt = withIds(o);
        // until the canvas exists, the directive's [options] carries the latest;
        // afterwards merge so series morph
        if (!this.chart) this.initial.set(opt);
        else if (this.chart && !this.chart.isDisposed()) this.chart.setOption(opt,
        { replaceMerge: ['series'] });
      });
    });
  }

  protected onInit(c: ECharts): void {
    this.chart = c;
  }
}

/** Give every series a stable id (name|stack|index) so replaceMerge maps it onto
the existing one and morphs. */
function withIds(o: EChartsCoreOption): EChartsCoreOption {
  const ss = (o as { series?: unknown }).series;
  if (!Array.isArray(ss)) return o;
  const series = ss.map((x: unknown, i: number) => {
    const s = x as Record<string, unknown>;
    return s['id'] !== undefined ? s : { ...s, id: `${String(s['name'] ?? '')}|${String(s['stack'] ?? '')}|${i}` };
  });
  return { ...o, series };
}

/** Evidence-desk chart styling (DESIGN.md section 2 + 3). */
export const INK = { ink: '#15171C', ink2: '#3D424D', ink3: '#6B7080', rule:
'#DDD6C8', sheet: '#FFFFF8', tc: '#2447D8', rs: '#C2361F' };
export function chartBase(): Record<string, unknown> {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Geist Variable, system-ui, sans-serif', color: INK.
    ink2, fontSize: 12 },
    animationDuration: 700, animationEasing: 'cubicOut', animationDurationUpdate:
    650, animationEasingUpdate: 'cubicInOut',
    tooltip: {
      backgroundColor: INK.sheet, borderColor: INK.rule, borderWidth: 1, padding:
      [10, 14],
      textStyle: { color: INK.ink, fontSize: 12 },
      extraCssText: 'box-shadow:0 12px 30px -10px rgba(40,30,10,.25); border-radius:10px;',
    },
  };
}
export function axis(): Record<string, unknown> {
  return {
    axisLine: { lineStyle: { color: INK.rule } }, axisTick: { show: false },
    axisLabel: { color: INK.ink3, fontSize: 11, fontFamily: 'Geist Mono Variable, monospace' },
    splitLine: { lineStyle: { color: INK.rule, type: [3, 4] } },
  };
}
