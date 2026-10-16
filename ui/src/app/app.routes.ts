import { Routes } from '@angular/router';

const t = (p: string) => `${p} – AwardShield`;
export const routes: Routes = [
  { path: '', title: 'AwardShield – every award, proven', loadComponent: () => import('./pages/landing').then((m) => m.Landing) },
  { path: 'case/:id', title: t('Decision'), loadComponent: () => import('./pages/decision').then((m) => m.Decision) },
  { path: 'case/:id/truecost', title: t('TrueCost'), loadComponent: () => import('./pages/truecost').then((m) => m.TrueCostPage) },
  { path: 'case/:id/engine', title: t('Engine'), loadComponent: () => import('./pages/engine').then((m) => m.EnginePage) },
  { path: 'case/:id/redseal', title: t('RedSeal'), loadComponent: () => import('./pages/redseal').then((m) => m.RedSealPage) },
  { path: 'case/:id/run', title: t('Agent run'), loadComponent: () => import('./pages/run').then((m) => m.RunPage) },
  { path: '**', redirectTo: '' },
];
