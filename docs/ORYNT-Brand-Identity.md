# ORYNT — Complete Brand Identity
## The Single Source of Truth for Everything Visual and Verbal
### Claude Code must read this entire document before building any frontend component

---

## VISION

To be the intelligence infrastructure every commerce business in the world relies on to make their next decision.

---

## MISSION

ORYNT gives every seller — from a WhatsApp trader in Lagos to a multi-brand operator in London — the same quality of business intelligence previously available only to corporations with data teams. Free for businesses. Funded by the institutions that need their data.

---

## VALUES

**Clarity over complexity.**
Every insight ORYNT produces must be understandable in under 10 seconds. If a seller cannot act on it immediately, it is not intelligence — it is noise.

**Data integrity above everything.**
Every number ORYNT shows is accurate or it is not shown. No estimates presented as facts. No vanity metrics.

**Built for the builder.**
ORYNT is for the person running the business, not the analyst studying it. Every feature exists to help someone make a better decision today.

**Global standard, local relevance.**
Built to the same standard as the best intelligence platforms in the world. Understands Paystack, WhatsApp orders, and Nigerian commerce in ways no global platform ever will.

**Trust is the product.**
Fintechs, investors, and suppliers pay for ORYNT data only if it is trustworthy. Every decision — engineering and product — is made with this in mind.

---

## BRAND PERSONALITY

ORYNT is not loud. It does not shout about features.
ORYNT is the most prepared person in the room — the one who speaks only when they have something worth saying, and when they do, everyone listens.

**Tone of voice:** Direct. Confident. Precise. Never condescending. Never casual to the point of unprofessional. Never corporate to the point of cold.

**ORYNT sounds like this:**
- "Your top product by margin this week is Ankara Tote Bag. 14 days of stock remaining. Reorder now."
- "3 customers who spent over ₦50,000 have gone quiet for 60 days. Here is what to send them."
- "Dead capital this week: ₦847,000 locked in 12 products. Here is how to recover it."

**ORYNT never sounds like this:**
- "Wow, great news! Your sales are up! 🎉"
- "We noticed some interesting trends you might want to explore!"
- "Your dashboard is ready to help you grow your business!"

---

## NAMING AND PRONUNCIATION

**Platform name:** ORYNT
**Pronunciation:** OR-int
**Origin:** From "orient" — to find your direction, to know exactly where you stand and where to go next.
**Domain:** getorynt.com (primary), orynt.app (product)
**Trademark:** File at FIPO Nigeria immediately. Madrid Protocol for international coverage after first revenue.

---

## LOGO SYSTEM

### Concept
The ORYNT logo is a wordmark combined with a minimal geometric mark. The mark is a compass needle — a single sharp directional arrow inside a precise circle, rotated 45 degrees northeast. It communicates orientation, direction, and forward motion without being literal or decorative.

### The Mark
```
Shape: A thin circle (stroke only, no fill) with a single sharp arrow inside,
       pointing to the upper-right at exactly 45 degrees (northeast).
       The arrow tip touches the circle boundary. The tail tapers to nothing.
       The circle diameter is exactly 1.4× the cap height of the wordmark.
Weight: The circle stroke and arrow stroke are identical weight — 1.5px at base size.
Feel:  Precise. Engineered. Not decorative. Not friendly. Purposeful.
```

### Wordmark
```
Text:           ORYNT
Case:           All caps, always
Letter spacing: +0.12em (slightly tracked out)
Font:           Syne (display weight 700) — geometric, distinctive, uncommon
                Available free at fonts.google.com/specimen/Syne
Alignment:      Mark on the left, wordmark on the right, vertically centered
Gap:            0.6× the cap height between mark and first letter
```

### Logo Variations
- **Primary (horizontal):** Mark + ORYNT wordmark side by side — use for header, marketing, documents
- **Mark only:** Circle + arrow alone — use for favicon, app icon, avatar, small placements
- **Stacked:** Mark centered above wordmark — use for square format only (social media profile)

### Logo Colors
- **On dark background (primary use):** Mark and wordmark in `#F4F4F6` (Orynt White)
- **On light background:** Mark and wordmark in `#0A0A0F` (Orynt Black)
- **Accent version:** Mark in `#00C9A7` (Orynt Teal), wordmark in `#F4F4F6` — use sparingly for emphasis

### Logo Rules
- Minimum size: 80px wide for horizontal, 24px for mark-only
- Clear space: equal to the height of the letter O on all sides
- Never use a gradient on the logo
- Never use a drop shadow on the logo
- Never stretch or distort
- Never place on a busy background without a solid backing
- Never change the letter spacing
- Never use a font other than Syne for the wordmark

---

## COLOR SYSTEM

### Core Palette

| Token | Hex | RGB | Usage |
|---|---|---|---|
| `--color-bg` | `#0A0A0F` | 10, 10, 15 | Primary page background |
| `--color-surface` | `#111118` | 17, 17, 24 | Card backgrounds, sidebar, panels |
| `--color-surface-raised` | `#17171F` | 23, 23, 31 | Elevated cards, dropdowns, modals |
| `--color-border` | `#1F1F2E` | 31, 31, 46 | All borders, dividers, separators |
| `--color-border-subtle` | `#161622` | 22, 22, 34 | Subtle separators, zebra rows |

### Text Palette

| Token | Hex | Usage |
|---|---|---|
| `--color-text-primary` | `#F4F4F6` | All primary text, headings, metric numbers |
| `--color-text-secondary` | `#9898AE` | Labels, subtitles, secondary info |
| `--color-text-muted` | `#5C5C73` | Placeholder text, disabled states, captions |
| `--color-text-inverse` | `#0A0A0F` | Text on teal/light backgrounds |

### Accent Palette

| Token | Hex | Usage |
|---|---|---|
| `--color-accent` | `#00C9A7` | Primary action — buttons, links, active nav, highlights, focus rings |
| `--color-accent-hover` | `#00B396` | Hover state for accent elements |
| `--color-accent-dim` | `rgba(0,201,167,0.08)` | Teal-tinted card backgrounds, badge fills |
| `--color-accent-border` | `rgba(0,201,167,0.20)` | Teal-tinted borders for active/selected states |

### Semantic Palette — SKU Verdict System

These four colors are the visual language of ORYNT intelligence. They must be used consistently and exclusively for their designated purpose.

| Token | Hex | Verdict | Meaning |
|---|---|---|---|
| `--color-scale` | `#22C55E` | Scale | Strong performance. Invest now. |
| `--color-scale-dim` | `rgba(34,197,94,0.08)` | Scale background | |
| `--color-monitor` | `#EAB308` | Monitor | Holding steady. Watch closely. |
| `--color-monitor-dim` | `rgba(234,179,8,0.08)` | Monitor background | |
| `--color-fix` | `#F97316` | Fix | Declining. Action needed soon. |
| `--color-fix-dim` | `rgba(249,115,22,0.08)` | Fix background | |
| `--color-kill` | `#EF4444` | Kill | Dead. Recover capital immediately. |
| `--color-kill-dim` | `rgba(239,68,68,0.08)` | Kill background | |

**Rule:** Red (`--color-kill`) is used ONLY for Kill verdict and critical errors. Never for decorative purposes. Never for warnings. Orange is for Fix. Green is for Scale. Yellow is for Monitor.

### Data Visualization Palette

Used exclusively for charts. Always in this order — never reassign meaning between charts on the same page.

| Order | Token | Hex | Use for |
|---|---|---|---|
| 1st | `--color-chart-1` | `#00C9A7` | Primary metric line / primary bar |
| 2nd | `--color-chart-2` | `#818CF8` | Secondary metric line / comparison |
| 3rd | `--color-chart-3` | `#FB923C` | Tertiary metric / third series |
| 4th | `--color-chart-4` | `#F472B6` | Fourth series |
| 5th | `--color-chart-5` | `#34D399` | Fifth series |
| Grid | `--color-chart-grid` | `#1F1F2E` | Chart gridlines |
| Axis | `--color-chart-axis` | `#5C5C73` | Axis labels and tick marks |
| Tooltip bg | `--color-chart-tooltip` | `#17171F` | Chart tooltip background |

### Status Colors

| Token | Hex | Usage |
|---|---|---|
| `--color-success` | `#22C55E` | Success states, connected integrations |
| `--color-warning` | `#EAB308` | Warnings, expiring tokens, attention needed |
| `--color-error` | `#EF4444` | Errors, failed syncs, disconnected |
| `--color-info` | `#818CF8` | Informational states, tips |
| `--color-neutral` | `#5C5C73` | Inactive, pending, not connected |

### Full CSS Variable Declaration

Add this to the global stylesheet. Every component references these variables — never hardcode hex values in components.

```css
:root {
  /* Backgrounds */
  --color-bg: #0A0A0F;
  --color-surface: #111118;
  --color-surface-raised: #17171F;
  --color-border: #1F1F2E;
  --color-border-subtle: #161622;

  /* Text */
  --color-text-primary: #F4F4F6;
  --color-text-secondary: #9898AE;
  --color-text-muted: #5C5C73;
  --color-text-inverse: #0A0A0F;

  /* Accent */
  --color-accent: #00C9A7;
  --color-accent-hover: #00B396;
  --color-accent-dim: rgba(0, 201, 167, 0.08);
  --color-accent-border: rgba(0, 201, 167, 0.20);

  /* SKU Verdicts */
  --color-scale: #22C55E;
  --color-scale-dim: rgba(34, 197, 94, 0.08);
  --color-monitor: #EAB308;
  --color-monitor-dim: rgba(234, 179, 8, 0.08);
  --color-fix: #F97316;
  --color-fix-dim: rgba(249, 115, 22, 0.08);
  --color-kill: #EF4444;
  --color-kill-dim: rgba(239, 68, 68, 0.08);

  /* Charts */
  --color-chart-1: #00C9A7;
  --color-chart-2: #818CF8;
  --color-chart-3: #FB923C;
  --color-chart-4: #F472B6;
  --color-chart-5: #34D399;
  --color-chart-grid: #1F1F2E;
  --color-chart-axis: #5C5C73;
  --color-chart-tooltip: #17171F;

  /* Status */
  --color-success: #22C55E;
  --color-warning: #EAB308;
  --color-error: #EF4444;
  --color-info: #818CF8;
  --color-neutral: #5C5C73;
}
```

---

## TYPOGRAPHY

### Typeface Decisions

**Display / Headings — Syne**
- Weight used: 600, 700, 800
- Google Fonts: `https://fonts.google.com/specimen/Syne`
- Import: `@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&display=swap')`
- Character: Geometric, slightly irregular, unmistakably distinctive at large sizes. Nothing generic about it.
- Use for: Page titles, section headings, large metric numbers, the logo wordmark

**Body / UI — DM Sans**
- Weight used: 400, 500, 600
- Google Fonts: `https://fonts.google.com/specimen/DM+Sans`
- Import: `@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap')`
- Character: Clean, neutral, highly legible at small sizes. Friendlier than Inter, more distinctive than system fonts.
- Use for: All UI text, labels, body copy, table content, form fields, navigation

**Monospace — JetBrains Mono**
- Weight used: 400, 500
- Google Fonts: `https://fonts.google.com/specimen/JetBrains+Mono`
- Import: `@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap')`
- Use for: API keys, order IDs, transaction references, tracking numbers, code snippets

### Type Scale

```css
/* Display — hero metric numbers, CIP Score */
--text-display:     font-family: Syne; font-size: 56px; font-weight: 800; line-height: 1.0; letter-spacing: -0.02em;

/* H1 — page titles */
--text-h1:          font-family: Syne; font-size: 32px; font-weight: 700; line-height: 1.2; letter-spacing: -0.01em;

/* H2 — section headings */
--text-h2:          font-family: Syne; font-size: 24px; font-weight: 700; line-height: 1.3; letter-spacing: -0.01em;

/* H3 — card titles, widget headings */
--text-h3:          font-family: Syne; font-size: 18px; font-weight: 600; line-height: 1.4; letter-spacing: 0;

/* Body Large — primary reading text */
--text-body-lg:     font-family: DM Sans; font-size: 16px; font-weight: 400; line-height: 1.6; letter-spacing: 0;

/* Body — standard UI text, table content */
--text-body:        font-family: DM Sans; font-size: 14px; font-weight: 400; line-height: 1.5; letter-spacing: 0;

/* Body Medium — emphasized UI text */
--text-body-med:    font-family: DM Sans; font-size: 14px; font-weight: 500; line-height: 1.5; letter-spacing: 0;

/* Small — labels, captions, metadata */
--text-small:       font-family: DM Sans; font-size: 12px; font-weight: 400; line-height: 1.4; letter-spacing: 0.01em;

/* Small Medium — active labels, tag text */
--text-small-med:   font-family: DM Sans; font-size: 12px; font-weight: 500; line-height: 1.4; letter-spacing: 0.02em;

/* Micro — badges, status chips, eyebrow labels */
--text-micro:       font-family: DM Sans; font-size: 11px; font-weight: 600; line-height: 1.3; letter-spacing: 0.06em; text-transform: uppercase;

/* Mono — IDs, references, API keys */
--text-mono:        font-family: JetBrains Mono; font-size: 13px; font-weight: 400; line-height: 1.5; letter-spacing: 0;
```

### Number Formatting Rules

These are not optional. Apply consistently across every number displayed in ORYNT.

```
Nigerian Naira amounts:
  Summary cards (large):     ₦4.2M  |  ₦850K  |  ₦12.4K
  Detail views (full):       ₦1,247,500  |  ₦84,200.00
  Inline text:               ₦1,247,500

Percentages:
  Positive change:   +14.2%  — color: --color-scale
  Negative change:   -8.7%   — color: --color-kill
  Neutral/flat:      0.0%    — color: --color-text-muted
  Always show sign (+/-) on trend percentages

SKU Scores:
  Display as:  8.4  (one decimal place, always)
  Never:       8.4/10 or 8.40 or 8
  Verdict badge always adjacent to score number

Dates:
  Short:    14 Feb  |  Today  |  Yesterday
  Medium:   14 Feb 2025
  Full:     Monday, 14 February 2025
  Time:     2:34 PM WAT
  Never use MM/DD/YYYY format
```

---

## SPACING SYSTEM

Base unit: 4px. All spacing is multiples of 4.

```css
--space-1:   4px    /* Tightest — icon-to-label gap */
--space-2:   8px    /* Between related inline elements */
--space-3:   12px   /* Compact component padding */
--space-4:   16px   /* Standard component padding (default) */
--space-5:   20px   /* Comfortable component padding */
--space-6:   24px   /* Between components in same section */
--space-8:   32px   /* Between sections */
--space-10:  40px   /* Major layout gaps */
--space-12:  48px   /* Page-level vertical rhythm */
--space-16:  64px   /* Hero/display sections */
```

---

## BORDER RADIUS

```css
--radius-sm:    4px    /* Tags, inline badges, small chips */
--radius-md:    8px    /* Buttons, inputs, small cards */
--radius-lg:    12px   /* Standard cards, panels */
--radius-xl:    16px   /* Large cards, modals */
--radius-2xl:   24px   /* Featured cards, hero elements */
--radius-full:  9999px /* Pill badges, avatar circles, toggles */
```

---

## SHADOWS AND ELEVATION

Dark UI shadows use opacity against the near-black background.
Never use shadows with color — only black opacity.

```css
--shadow-sm:   0 1px 2px rgba(0, 0, 0, 0.4);               /* Subtle — inline elements */
--shadow-md:   0 2px 8px rgba(0, 0, 0, 0.5);               /* Cards */
--shadow-lg:   0 4px 16px rgba(0, 0, 0, 0.6);              /* Dropdowns, tooltips */
--shadow-xl:   0 8px 32px rgba(0, 0, 0, 0.7);              /* Modals */
--shadow-accent: 0 0 0 1px var(--color-accent-border);     /* Focus ring, active state */
--shadow-focus:  0 0 0 3px rgba(0, 201, 167, 0.20);        /* Keyboard focus ring */
```

---

## LAYOUT STRUCTURE

### Sidebar
```
Width:          240px fixed (desktop) | 64px collapsed (tablet) | off-canvas (mobile)
Background:     var(--color-surface)
Border right:   1px solid var(--color-border)
Top section:    Logo area — 64px tall, padding 0 20px
Brand switcher: Below logo, 56px tall
Navigation:     Below brand switcher, full remaining height minus bottom section
Bottom section: User profile row — 64px tall
```

### Main Content Area
```
Background:        var(--color-bg)
Left margin:       240px (sidebar width)
Top bar:           64px tall, sticky
Padding:           32px (desktop) | 20px (tablet) | 16px (mobile)
Max content width: 1400px centered within the content area
```

### Top Bar
```
Height:        64px
Background:    var(--color-bg) with 1px bottom border var(--color-border)
Contents:      Search bar (left) | Notification bell + Avatar (right)
Position:      Sticky, z-index 50
```

### Page Layout Pattern (all dashboard pages follow this)
```
Row 1: Page header — title (H1) + subtitle (body, muted) + action buttons (right aligned)
       Height: auto, padding-bottom: 24px

Row 2: Metric cards row — 4 cards equal width, 16px gap
       Height: auto

Row 3: Charts row — main chart (flex: 2) + side panel (flex: 1), 16px gap
       Height: 380px

Row 4: Data table — full width, with search + filters above
       Height: auto, min 400px
```

---

## COMPONENT SPECIFICATIONS

### Metric Card
The most important component in ORYNT. Every number displayed must follow this exact structure.

```
Container:
  background:     var(--color-surface)
  border:         1px solid var(--color-border)
  border-radius:  var(--radius-lg)
  padding:        24px
  min-height:     140px

Contents (top to bottom):
  1. Label row:
     - Icon (16px, color: var(--color-text-muted)) + Label text (--text-micro, muted, uppercase)
     - Margin bottom: 12px

  2. Primary number:
     - Font: Syne 700, 36px, color: var(--color-text-primary)
     - Line height: 1.0
     - Margin bottom: 8px

  3. Change indicator:
     - Percentage (--text-small-med) + "vs last week" (--text-small, muted)
     - Positive: color var(--color-scale) + ↑ arrow
     - Negative: color var(--color-kill) + ↓ arrow
     - Flat: color var(--color-text-muted) + → arrow

  4. Sparkline (optional):
     - 48px tall, full card width minus padding
     - Single line, color var(--color-chart-1)
     - No axes, no labels, no tooltip — purely decorative trend indicator
     - Margin top: 16px
```

### SKU Score Badge
The signature visual element of ORYNT. Non-negotiable specifications.

```
Score number:
  Font:    Syne 700, 28px
  Color:   var(--color-text-primary)

Verdict chip (adjacent, vertically centered):
  Font:    --text-micro (DM Sans 600, 11px, uppercase, letter-spacing 0.06em)
  Padding: 4px 10px
  Radius:  var(--radius-full)

  Scale:   background var(--color-scale-dim)  | text var(--color-scale)  | border 1px solid rgba(34,197,94,0.20)
  Monitor: background var(--color-monitor-dim)| text var(--color-monitor)| border 1px solid rgba(234,179,8,0.20)
  Fix:     background var(--color-fix-dim)    | text var(--color-fix)    | border 1px solid rgba(249,115,22,0.20)
  Kill:    background var(--color-kill-dim)   | text var(--color-kill)   | border 1px solid rgba(239,68,68,0.20)

Rule: NEVER show the score without the verdict chip. NEVER show the verdict chip without the score.
```

### Primary Button
```
Background:     var(--color-accent)
Text:           var(--color-text-inverse), DM Sans 600, 14px
Padding:        10px 20px
Border radius:  var(--radius-md)
Border:         none
Height:         40px

Hover:          background var(--color-accent-hover), transition 150ms ease
Active:         opacity 0.9
Focus:          box-shadow var(--shadow-focus)
Disabled:       opacity 0.4, cursor not-allowed

Icon + text:    Icon 16px, gap 8px between icon and label
```

### Secondary Button
```
Background:     transparent
Text:           var(--color-text-primary), DM Sans 500, 14px
Padding:        10px 20px
Border radius:  var(--radius-md)
Border:         1px solid var(--color-border)
Height:         40px

Hover:          background var(--color-surface-raised), border-color var(--color-text-muted)
Focus:          box-shadow var(--shadow-focus)
```

### Ghost Button
```
Background:     transparent
Text:           var(--color-text-secondary), DM Sans 500, 14px
Padding:        10px 20px
Border:         none
Height:         40px

Hover:          text color var(--color-text-primary), background rgba(255,255,255,0.04)
```

### Input Field
```
Background:     var(--color-surface)
Border:         1px solid var(--color-border)
Border radius:  var(--radius-md)
Padding:        10px 14px
Height:         40px
Font:           DM Sans 400, 14px, color var(--color-text-primary)
Placeholder:    color var(--color-text-muted)

Focus:          border-color var(--color-accent), box-shadow var(--shadow-focus), outline none
Error:          border-color var(--color-error), box-shadow 0 0 0 3px rgba(239,68,68,0.15)
Disabled:       opacity 0.5, cursor not-allowed
```

### Data Table
```
Container:
  background:    var(--color-surface)
  border:        1px solid var(--color-border)
  border-radius: var(--radius-lg)
  overflow:      hidden

Header row:
  background:    var(--color-surface-raised)
  padding:       12px 16px
  font:          --text-micro (uppercase, muted)
  border-bottom: 1px solid var(--color-border)

Data rows:
  padding:       14px 16px
  font:          --text-body
  border-bottom: 1px solid var(--color-border-subtle)
  height:        52px

  Even rows:     background var(--color-surface)
  Odd rows:      background rgba(255,255,255,0.01)
  Hover:         background var(--color-surface-raised)
  Selected:      background var(--color-accent-dim), border-left 3px solid var(--color-accent)

Sort indicator: Arrow icon 12px, muted when inactive, accent when active
Empty state:    Centered, icon 48px muted, heading H3, body muted, one primary action button
```

### Navigation Item (Sidebar)
```
Default:
  padding:       10px 16px
  border-radius: var(--radius-md)
  font:          DM Sans 500, 14px, color var(--color-text-secondary)
  icon:          16px, color var(--color-text-muted)
  gap:           10px between icon and label

Hover:
  background:    rgba(255,255,255,0.04)
  text color:    var(--color-text-primary)
  icon color:    var(--color-text-secondary)

Active (current page):
  background:    var(--color-accent-dim)
  text color:    var(--color-accent)
  icon color:    var(--color-accent)
  border-left:   2px solid var(--color-accent) — sits flush with sidebar left edge
```

### Brand Switcher (Sidebar)
```
Container:
  padding:       8px 12px
  margin:        8px
  border:        1px solid var(--color-border)
  border-radius: var(--radius-md)
  background:    var(--color-surface-raised)
  cursor:        pointer

Contents:
  Brand icon:    24px circle, background var(--color-accent-dim), icon color var(--color-accent)
  Brand name:    DM Sans 600, 13px, color var(--color-text-primary), truncated with ellipsis
  Category:      DM Sans 400, 11px, color var(--color-text-muted)
  Chevron:       16px icon, color var(--color-text-muted), rotates 180deg when open

Hover:           border-color var(--color-accent-border)

Dropdown:
  background:    var(--color-surface-raised)
  border:        1px solid var(--color-border)
  border-radius: var(--radius-lg)
  padding:       8px
  box-shadow:    var(--shadow-lg)
  min-width:     220px
  max-height:    320px, scrollable

  Each brand item:
    padding:     10px 12px
    border-radius: var(--radius-md)
    Active brand: background var(--color-accent-dim), checkmark icon right
    Hover:       background rgba(255,255,255,0.04)

  Divider:       1px solid var(--color-border), margin 4px 0

  Add New Brand button:
    padding:     10px 12px
    color:       var(--color-accent)
    icon:        Plus 16px
    font:        DM Sans 500, 13px
    hover:       background var(--color-accent-dim)
```

### Status Chip / Badge
```
Base:
  font:          --text-micro
  padding:       3px 8px
  border-radius: var(--radius-full)
  display:       inline-flex, align-items center, gap 4px
  dot:           6px circle, filled

Connected:  background rgba(34,197,94,0.08)  | text #22C55E  | dot #22C55E
Error:      background rgba(239,68,68,0.08)  | text #EF4444  | dot #EF4444
Pending:    background rgba(234,179,8,0.08)  | text #EAB308  | dot #EAB308
Inactive:   background rgba(92,92,115,0.08)  | text #5C5C73  | dot #5C5C73
Info:       background rgba(129,140,248,0.08)| text #818CF8  | dot #818CF8
```

### Toast / Notification
```
Container:
  background:    var(--color-surface-raised)
  border:        1px solid var(--color-border)
  border-radius: var(--radius-lg)
  padding:       14px 16px
  box-shadow:    var(--shadow-xl)
  max-width:     380px
  border-left:   3px solid (verdict color)

Success: border-left-color var(--color-success)
Error:   border-left-color var(--color-error)
Warning: border-left-color var(--color-warning)
Info:    border-left-color var(--color-info)
```

---

## ICONOGRAPHY

Use **Lucide React** exclusively. No mixing icon libraries.
- Import: `import { IconName } from 'lucide-react'`
- Standard size: 16px in nav, 18px in buttons, 20px in cards, 24px in empty states
- Stroke width: 1.5px (Lucide default) — never change this
- Color: always inherits from parent text color unless explicitly overridden

Navigation icons (assign these specifically — do not swap):
```
Overview:         LayoutDashboard
SKU Intelligence: Layers
Customers:        Users
Orders:           ShoppingBag
Channels:         GitBranch
Ads/Influencers:  Megaphone
Automations:      Zap
Weekly Digest:    Mail
Integrations:     Plug
Settings:         Settings
Add Brand:        PlusCircle
Notification:     Bell
Search:           Search
Logout:           LogOut
```

---

## ANIMATION AND MOTION

```
Standard transition:   150ms ease
Hover transition:      100ms ease
Modal enter:           200ms ease-out, translate Y from +8px to 0, opacity 0 to 1
Modal exit:            150ms ease-in
Dropdown open:         150ms ease-out, translate Y from -4px to 0, opacity 0 to 1
Toast enter:           200ms ease-out, translate X from +16px to 0, opacity 0 to 1
Number count-up:       600ms ease-out — use on metric card numbers when data first loads
Skeleton loading:      1.5s ease-in-out infinite pulse between surface and surface-raised
Page transition:       None — instant. Data dashboards do not animate page changes.
```

**Rules:**
- Never animate data loading delays — show skeleton states immediately
- Never use bounce or elastic easing — these are not appropriate for a professional intelligence platform
- Chart line draw animation: 600ms ease-out on initial render only — not on data updates
- Never block user interaction with animations

---

## SIDEBAR NAVIGATION ORDER

This is the definitive order. Do not rearrange.

```
1.  Overview              (LayoutDashboard)
2.  SKU Intelligence      (Layers)
3.  Customers             (Users)
4.  Orders                (ShoppingBag)
5.  Channels              (GitBranch)
6.  Ads & Influencers     (Megaphone)
7.  Automations           (Zap)
8.  Weekly Digest         (Mail)
9.  ────── divider ──────
10. Integrations          (Plug)
11. Settings              (Settings)
```

---

## WHAT THE UI MUST NEVER DO

- Use purple as an accent color anywhere — it is gone, replaced by ORYNT Teal
- Hardcode hex values in components — always reference CSS variables
- Use gradients on solid backgrounds (charts only, never backgrounds or cards)
- Use more than two accent colors on a single page
- Show empty states without a single clear call-to-action
- Display a number without context — always show comparison or trend
- Use transitions longer than 300ms
- Show red for anything other than Kill verdict or system errors
- Use Inter, Roboto, or system fonts anywhere — Syne and DM Sans only
- Use box shadows with color — black opacity only
- Apply border-radius larger than 24px on any component

---

## TAILWIND CONFIGURATION

Add these to `tailwind.config.js` to make brand tokens available as Tailwind classes:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        'orynt-bg':             '#0A0A0F',
        'orynt-surface':        '#111118',
        'orynt-surface-raised': '#17171F',
        'orynt-border':         '#1F1F2E',
        'orynt-text':           '#F4F4F6',
        'orynt-text-secondary': '#9898AE',
        'orynt-text-muted':     '#5C5C73',
        'orynt-accent':         '#00C9A7',
        'orynt-accent-hover':   '#00B396',
        'orynt-scale':          '#22C55E',
        'orynt-monitor':        '#EAB308',
        'orynt-fix':            '#F97316',
        'orynt-kill':           '#EF4444',
        'orynt-chart-1':        '#00C9A7',
        'orynt-chart-2':        '#818CF8',
        'orynt-chart-3':        '#FB923C',
        'orynt-chart-4':        '#F472B6',
      },
      fontFamily: {
        'display': ['Syne', 'sans-serif'],
        'body':    ['DM Sans', 'sans-serif'],
        'mono':    ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'sm':   '4px',
        'md':   '8px',
        'lg':   '12px',
        'xl':   '16px',
        '2xl':  '24px',
      },
    },
  },
}
```

---

## GLOBAL STYLESHEET SETUP

Add to `app/globals.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  background-color: #0A0A0F;
  color: #F4F4F6;
  font-family: 'DM Sans', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  background-color: var(--color-bg);
  color: var(--color-text-primary);
  min-height: 100vh;
}

/* Custom scrollbar — dark, minimal */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--color-surface); }
::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-text-muted); }

/* Selection */
::selection { background: rgba(0, 201, 167, 0.20); color: var(--color-text-primary); }

/* Focus visible — keyboard navigation */
:focus-visible { outline: none; box-shadow: var(--shadow-focus); border-radius: 4px; }
```

---

## FIRST IMPLEMENTATION TASK FOR CLAUDE CODE

Before building any feature in Sprint 1, implement the brand system in this exact order:

1. Update `tailwind.config.js` with the full color and font configuration above
2. Replace `app/globals.css` entirely with the global stylesheet above
3. Add the CSS variable block to `globals.css`
4. Update `app/layout.tsx` to set `<html>` background to `#0A0A0F` and use DM Sans as default font
5. Rebuild the sidebar using the exact specifications above — new colors, Syne for the ORYNT wordmark, brand switcher component, correct navigation items and icons in the correct order
6. Rebuild the top bar with the correct background, search, and avatar
7. Update the Overview page to use the correct card styles, typography scale, and color variables
8. Confirm the current purple is completely gone — search the entire codebase for any hardcoded purple hex values (`#7C3AED`, `#6D28D9`, `#8B5CF6`, `#A78BFA`) and replace them with the correct ORYNT tokens

Only after all eight steps are complete and confirmed in the browser should Sprint 1 Task 1.2 begin.

---

*Document: ORYNT Brand Identity and Design System*
*Version: 1.0 — Approved*
*Status: Active — governs all frontend decisions from this point forward*
*Last updated: Sprint 1 commencement*
