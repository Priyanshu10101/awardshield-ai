/** Tree-shaken ECharts build: only what AwardShield uses (lazy chunk). */
import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent,
TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent,
MarkLineComponent, MarkPointComponent, CanvasRenderer]);

export * from 'echarts/core';
export default echarts;
