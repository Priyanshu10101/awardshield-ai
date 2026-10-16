# AwardShield Design System – "Evidence Desk"

## 0. Research Log
- Embedded refs: shortlisted `linear.app`, `stripe`, `claude` (editorial paper) -> picked Layer A `soft-skill` (premium, generous whitespace, nested surfaces, spring motion) + Layer B `linear.app` (precision, hairline borders, tight display tracking, mono for technical data). Linear's dark canvas is NOT taken; its precision is.
- Design council (4 sub-agents, parallel): Opus -> light "evidence desk" (paper, ink, highlighter, wax seal; self-annotating award document hero; "two pens on one page"); artistry -> forensic lightbox (dark, UV cyan / vermilion, serif display, story / executive toggle); visual-engineering -> obsidian (dark, buildable ECharts list: bullet, waterfall, heatmap, lazy charts); strategist -> sell defensible decisions, never "OVERTURNED" (contested) headline, plain words, replay run.
Decision: light evidence desk (Opus) + dark "engine console" band (one place, for deterministic code) + strategist's honest verdict language + visual-eng chart list.
- Old TrueCost "aurora glass" (dark, drifting indigo/violet/cyan blobs, glass cards) explicitly retired: 3 of 4 council members called it generic "AI demo"; blur and blobs wash out on projectors and recordings.
- Lazyweb / Imagen lanes: skipped (no image generation in this environment); the hero is built as SVG/CSS art instead.

## 1. Atmosphere & Identity
A procurement evidence desk under good light: warm paper, ink-black type, a cobalt pen that sources every number, a graphite ledger that computes, and a red wax seal that challenges. Calm, exact, audit-grade – the opposite of an AI toy.
**Signature:** The award document that marks itself up – TrueCost highlights in cobalt, the engine writes the 12-year total in the margin, RedSeal strikes the figure in red and presses the seal. Two pens, one page, one truth.
Colour IS meaning: cobalt = TrueCost (builds), red = RedSeal (challenges), graphite = engine (decides). Red is never a generic "bad" colour in this product.

## 2. Color

| Role | Token | Value | Usage |
|---|---|---|---|
| Canvas | `--paper` | `#F4F1EA` | page background (warm paper) |
| Canvas deep | `--paper-2` | `#ECE7DC` | alternating bands, insets |
| Sheet | `--sheet` | `#FFFFF8` | documents, cards (slightly warm white) |
| Ink | `--ink` | `#15171C` | primary text, engine identity |
| Ink 2 | `--ink-2` | `#3D424D` | body text |
| Ink 3 | `--ink-3` | `#6B7080` | captions, metadata (AA on paper: 4.9:1) |
| Rule | `--rule` | `#DDD6C8` | hairlines |
| Rule strong | `--rule-2` | `#C9C0AE` | input borders, table heads |
| TrueCost | `--tc` | `#2447D8` | cobalt pen: sources, extraction, links |
| TrueCost ramp | `--tc-50` / `-100` / `-700` | `#EEF2FF` / `#DCE4FF` / `#1A34A6` | tints, hover, pressed |
| RedSeal | `--rs` | `#C2361F` | sealing wax: challenges, strikes, verdict |
| RedSeal ramp | `--rs-50` / `-100` / `-700` | `#FDF0EC` / `#F8DAD2` / `#8E2414` | tints, seal shading |
| Highlighter | `--h1` | `#FFE58A` | verbatim quotes (text bg only) |
| Robust | `--ok` | `#1E7A4F` | CERTIFIED_ROBUST, "verified" check |
| Amber | `--warn` | `#B26A00` | "contested", "decision required" |
| Console bg | `--console` | `#0E1013` | the one dark band (engine) |
| Console line | `--console-line` | `rgba(255,255,255,.09)` | hairlines on console |
| Console text | `--console-ink` / `-2` | `#F2F0EA` / `#9DA3AE` | text on console |
| Google AI | `--g-blue/-red/-yellow/-green` | `#4285F4` / `#EA4335` / `#FBBC04` / `#34A853` | ONLY in the "Built with Google AI" strip |

Rules: accents are meaning, never decoration. Bidders get stable neutral-ish series colours in charts:
GreenMetro `#2F7D5B`, MetroLink `#2447D8`, UrbanDrive `#8A6F3E` (MetroLink = cobalt only coincidentally, so charts mark the WINNER with ink outline, not colour).

## 3. Typography
- Display: **Instrument Serif** (400, italic for emphasis) - legal-document gravitas for headlines only.
- UI / body: **Geist Variable** (400 / 500 / 600) - precise, not Inter.
- Mono: **Geist Mono Variable** - every number, quote, clause, id. Rule: if it came from a PDF or from code, it is mono.

| Level | Size | Weight | LH | Tracking | Usage |
|---|---|---|---|---|---|
| Hero | clamp(44px, 6.2vw, 92px) | Serif 400 | 0.98 | -0.02em | landing headline |
| Display | clamp(32px, 3.6vw, 52px) | Serif 400 | 1.05 | -0.015em | section titles |
| H1 | 28px | Geist 600 | 1.2 | -0.02em | page titles |
| H2 | 20px | Geist 600 | 1.3 | -0.01em | card titles |
| Lead | 19px | Geist 400 | 1.55 | -0.005em | hero sub, intros |
| Body | 15.5px | Geist 400 | 1.6 | 0 | default |
| Small | 13.5px | Geist 400 | 1.5 | 0 | secondary |
| Overline | 11.5px | Geist 600 | 1.3 | 0.12em upper | section labels |
| Figure | 15px | Mono 500 tnum | 1.4 | 0 | table numbers |
| Big figure | clamp(30px, 3.2vw, 44px) | Mono 500 tnum | 1.0 | -0.03em | KPIs |

## 4. Spacing & Layout
Base 4px: `--s1 4, --s2 8, --s3 12, --s4 16, --s5 20, --s6 24, --s8 32, --s10 40, --s12 48, --s16 64, --s20 80, --s24 96, --s32 128`.
Content max 1200px (`--wrap`), reading max 680px. Sections: `--s24` vertical (mobile `--s16`). Grid gutters `--s6`.
Radius: `--r1 6` (chips, inputs), `--r2 10` (buttons), `--r3 16` (cards), `--r4 24` (document sheet, bezels), pill 999.
Breakpoints: 640 / 900 / 1200. Below 900 every split becomes one column; no horizontal scroll at 375.

## 5. Components
- **Top bar**: floating pill (sheet, rule border, soft shadow), logo seal + wordmark, nav links, "Open the audit" button.
States: link hover ink underline; active route cobalt dot. Mobile: links collapse to a menu button.
- **Button**: `.btn` primary = ink fill, paper text, pill, trailing icon in its own circle (button-in-button);
`.btn-ghost` = transparent + rule border; `.btn-tc` cobalt; hover: icon circle translates 2px, press scale .98;
focus: 2px cobalt ring offset 2px; disabled .45 opacity.
- **Sheet** (double bezel): outer `--paper-2` tray 6px padding + rule, inner `--sheet` with inner highlight; radius `--r4`/`--r4-6`. Used for the hero document and key panels.
- **Card**: sheet bg, 1px rule, `--r3`, shadow-1; hover (if clickable) lift 2px + shadow-2.
- **Pen marks** (signature primitives): `.mark-tc` cobalt highlight sweep under text; `.strike-rs` red strike line drawn left->right; `.margin-note` handwritten-like note in mono with a leader line; `.seal` red wax SVG stamp.
- **Quote chip**: highlighter bg + mono text + "p.14 · BID_1" source tag; click -> evidence drawer.
- **Status pill**: verified (ok), contested (warn), rejected (ink-3 strike), finding (tc), AI (tc-50 bg), CODE (console).
- **Pipeline rail**: 5 nodes with AI / CODE / AI+PROOF badges, connectors animate a travelling dot.
- **Act stepper**: 3 tabs (Quoted rate / 12-year cost / After RedSeal) with sliding indicator; drives the acts chart.
- **Evidence drawer**: right slide-over (sheet), document name, page, quote with highlighter, source URL; Esc closes.
- **Data table**: hairline rows, mono right-aligned numbers, sticky head on paper-2.
- **Console band**: dark section with mono code lines + live numbers (engine).
- **Agent tree**: SVG/HTML tree of the ADK agents with Gemini badge per LLM agent, Python badge per code step.
Accessibility for all: visible focus, keyboard reachable, aria-labels on icon buttons, tabs with role=tablist.

## 6. Motion & Interaction
| Type | Duration | Easing | Usage |
|---|---|---|---|
| Micro | 140ms | cubic-bezier(.2,.8,.2,1) | hover, press |
| Standard | 260ms | cubic-bezier(.2,.8,.2,1) | tabs, drawer |
| Emphasis | 620ms | cubic-bezier(.16,1,.3,1) | reveals, chart morph |
| Seal | 520ms | cubic-bezier(.34,1.56,.64,1) | stamp press (scale 1.6 -> 1, rotate -12deg) |

Hero choreography (once, ~7s, replay button): 0.4s cobalt highlights sweep on rate + formula (TrueCost tags appear) ->
2.2s margin note writes "12-yr cost 549.02 cr · rank 1" -> 3.8s red strike through "63.00", note "words say Sixty Six"
-> 5.0s rank flips 1->2 -> 5.6s seal presses "NOT ROBUST". Only transform / opacity / clip-path / stroke-dashoffset.
Scroll reveals via IntersectionObserver (fade + 16px rise, 620ms).
`prefers-reduced-motion`: everything jumps to the final state, no loops.

## 7. Depth & Surface
Strategy: **mixed - paper tonal steps + soft warm shadows**, hairline rules. No glass, no blur on scrolling content.
| Level | Value | Usage |
|---|---|---|
| shadow-1 | `0 1px 2px rgba(40,30,10,.06), 0 1px 1px rgba(40,30,10,.04)` | cards at rest |
| shadow-2 | `0 6px 18px -6px rgba(40,30,10,.14), 0 2px 4px rgba(40,30,10,.05)` | hover, top bar |
| shadow-doc | `0 30px 60px -20px rgba(40,30,10,.25), 0 12px 24px -12px rgba(40,30,10,.12)` | hero document |

Paper grain: one fixed pointer-events-none SVG noise overlay at 3% opacity.

## 8. Accessibility Constraints & Accepted Debt
WCAG 2.2 AA: text >= 4.5:1 on paper (ink-3 `#6B7080` on `#F4F1EA` = 4.9:1), focus ring always visible, full keyboard, reduced motion respected, colour never the only signal (status pills carry icon + word; charts label values).
| Item | Location | Why accepted | Exit |
|---|---|---|---|
| No light/dark toggle | global | light evidence desk is the brand; console band covers dark | add if requested |
| Run page is a replay of a recorded run | `/case/:id/run` | judges must not wait 8 min; labelled "replay" | live runs via API later |
