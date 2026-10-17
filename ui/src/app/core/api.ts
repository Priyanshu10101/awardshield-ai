import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

export type Ranking = [string, number][];
export interface Bidder {
  name: string; rate: number; rate_param: string; amount_in_words: string;
  sticker_cr: number; lifetime_cr: number; year_one_cr: number; factor_end: number;
  fixed: number | null; terms: [string, number][];
}
export interface CaseOverview {
  id: string; title: string; buyer: string; country: string; currency: string;
  start: string; months: number; base_year: number;
  discount: { annual: number; monthly: number; method: string };
  volume: { id: string; label: string; build: string; components: [string, number, string][][] };
  bidders: Bidder[];
  acts: {
    sticker: { ranking: Ranking; winner: string };
    lifetime: { ranking: Ranking; winner: string; margin_cr: number };
    after: { ranking: Ranking; winner: string; challenge: string; change: string } | null;
    year_one_winner: string;
  };
  verdict: {
    status: 'OVERTURNED' | 'UNDERSTATED' | 'CERTIFIED_ROBUST'; contested: boolean;
    original_winner: string;
    final_winner: string; summary: string; fragile: boolean;
    narrative: { headline: string; findings: string[]; recommendation: string } |
    null;
  } | null;
}
export interface Evidence { document: string; page?: string; quote: string }
export interface Challenge {
  challenge_id: string; agent: string; kind: string; target: string; supplier:
  string;
  original_value: string; corrected_value: string; status: 'verified' |
  'contested' | 'rejected' | 'finding';
  checks: string[]; evidence: Evidence[]; evidence_against: Evidence[]; reasoning:
  string;
  overrides: Record<string, unknown>; rerun: { label: string; ranking: Ranking;
  winner: string; margin_cr: number } | null;
  effect: string;
}
export interface ProofPack {
  rfq_id: string; status: string; contested: boolean; original_winner: string;
  final_winner: string;
  baseline: { ranking: Ranking; winner: string; margin_cr: number };
  challenges: Challenge[];
  flip_thresholds: { supplier: string; param: string; current: number; threshold:
  number; change_pct: number; against: string; plausible: boolean }[];
  sensitivity: { driver: string; low_label: string; high_label: string; winner_low:
  string; winner_high: string; swing_cr: number; flips: boolean }[];
  fragile: boolean; summary: string;
  narrative: { headline: string; findings: string[]; recommendation: string } |
  null;
}
export interface RunEvent { t: number; agent: string; kind: 'call' | 'result' |
  'done'; name: string; detail: string; tokens?: number }
export interface RunRecord { run: string; rfq_id: string; started_at: string;
  duration_s: number; events: RunEvent[]; bidders?: string[]; verdict?: string }
export interface WhatIf {
  award: { ranking: Ranking; winner: string; runner_up: string; margin_cr: number;
  margin_pct: number };
  sticker: { ranking: Ranking; winner: string };
  yearly: Record<string, Record<string, number>>;
  factors: Record<string, Record<string, number>>;
  discount: { annual: number }; months: number; start: string;
}

@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private cache = new Map<string, Observable<unknown>>();

  private get<T>(url: string): Observable<T> {
    if (!this.cache.has(url)) this.cache.set(url, this.http.get<T>(url).pipe(
    shareReplay(1)));
    return this.cache.get(url) as Observable<T>;
  }
  case(id: string) { return this.get<CaseOverview>(`api/cases/${encodeURIComponent(id)}`); }
  truecost(id: string) { return this.get<any>(`api/cases/${encodeURIComponent(id)}/truecost`); }
  engine(id: string) { return this.get<any>(`api/cases/${encodeURIComponent(id)}/engine`); }
  redseal(id: string) { return this.get<ProofPack>(`api/cases/${encodeURIComponent(id)}/redseal`); }
  runs(id: string) { return this.get<Record<string, RunRecord>>(`api/cases/${encodeURIComponent(id)}/runs`); }
  evaluate(id: string, overrides: Record<string, unknown>) {
    return this.http.post<WhatIf>(`api/cases/${encodeURIComponent(id)}/evaluate`, {
    overrides });
  }
  docUrl(id: string, name: string) { return `api/cases/${encodeURIComponent(id)}/documents/${encodeURIComponent(name)}`; }
}

export const CASE_ID = 'IN-CRUT-EBUS';
export const BIDDER_COLOR: Record<string, string> = { GreenMetro: '#2F7D5B',
MetroLink: '#2447D8', UrbanDrive: '#8A6F3E' };
// a missing figure (a bidder without a complete cost model) shows as '-' instead of breaking the page
export const cr = (v: number | null | undefined, d = 2) => v == null || !isFinite(v) ? '-' : `₹${v.toLocaleString('en-IN', {
minimumFractionDigits: d, maximumFractionDigits: d })} cr`;
export const inr = (v: number | null | undefined) => v == null || !isFinite(v) ? '-' : `₹${v.toFixed(2)}`;
