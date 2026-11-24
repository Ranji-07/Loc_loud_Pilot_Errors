# Design system

Source of truth for colours: `colur.md` ("Forest Ochre"). Implementation: `apps/web/src/index.css` (CSS variables plus Tailwind 4 `@theme inline`), `apps/web/src/theme.ts` (dark, light, system), `apps/web/src/ui.tsx` (shared components).

## Colour tokens

The nine base colours are used exactly as given in `colur.md`. Derived tokens are mixes of those colours only.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | #121513 | #F5F8F6 | Page background, inputs |
| `--surface` | #1B1F1C | #FFFFFF | Cards, sidebar, dialogs |
| `--border` | #323833 | #DDE7E1 | Decorative 1px borders |
| `--text` | #E8EBE5 | #141A16 | All body text, badge text |
| `--accent` | #FFBA00 | #1E7F57 | Primary button, active nav icon, focus ring, selected tab |
| `--on-accent` | #121513 | #FFFFFF | Text on accent |
| `--success` / `--warning` / `--danger` | #4FB286 / #E3A84B / #E5686B | #1E8A5C / #B7791F / #D13F43 | Status dots, soft fills, error borders, danger text on cards |
| `--muted` (derived) | 70% text + 30% surface | same rule | Secondary text |
| `--surface-2` (derived) | 6% text on surface | same rule | Hover, selected row |
| `--border-strong` (derived) | 45% text on surface | same rule | Input and search borders (need 3:1) |
| `--*-soft` (derived) | 15% colour on surface | same rule | Badge and alert backgrounds |

### Contrast (WCAG 2.1, measured)

| Pair | Dark | Light |
|---|---|---|
| text on surface | 13.85 | 17.66 |
| muted on surface / bg | 7.41 / 8.17 | 6.49 / 6.07 |
| on-accent on accent | 10.75 | 4.97 |
| accent on surface | 9.75 | 4.97 |
| danger on surface | 5.18 | 4.66 |
| success on surface | 6.39 | 4.33 (below 4.5) |
| warning on surface | 7.92 | 3.64 (below 4.5) |

Rule that follows from this: **status text is never drawn in the status colour.** Badges use `--text` on the soft fill (at least 10:1 in both themes) and carry the colour in a dot. Success and warning colours appear only as dots, borders and fills (non-text needs 3:1, which both meet). axe-core (WCAG 2 A/AA) reports 0 violations on Overview (both themes), Decisions and Agents.

## Type, spacing, shape, motion

- Font: system UI stack; mono: Cascadia Code, Consolas. Sizes: 11px (group labels), 12px (meta), 14px (body), 20px (page title).
- Spacing: Tailwind 4px scale. One radius: `--radius` 6px (`rounded-ui`).
- Icons: lucide-react only, 16px in content, 14px in controls.
- No gradients, glass or decorative animation. Only the loading spinner and the streaming cursor animate, and `prefers-reduced-motion` turns both off.
- Focus: 2px accent outline on `:focus-visible`. Skip-to-content link.

## Navigation map

```
WORKSPACE      Overview · Projects* · Agents · Tasks*
INTELLIGENCE   Prompt Studio · Decisions (Approvals | Decisions*) · Knowledge*
OPERATIONS     History · Models · Infrastructure (Health | Resources | Logs | Setup guides) · Costs
SYSTEM         Settings (read-only backend, editable browser Appearance)
```

`*` = no backend yet; the screen says what is missing (see docs/PENDING.md). Old links keep working: `#/agent`, `#/audit`, `#/usage`, `#/setup/<id>`. Ctrl+K opens the command palette (pages, new task, pending approvals, theme). Under 1024px the sidebar becomes a menu drawer.

## Component inventory

| Component | Where | States |
|---|---|---|
| AppLayout, Sidebar (groups collapse and are remembered), ThemeSwitch, system status | `App.tsx` | backend offline, checking, issues, OK |
| CommandPalette (native `<dialog>`, arrow keys, Enter, Esc) | `CommandPalette.tsx` | no matches |
| PageHeader, Card, Tabs, StatusBadge | `ui.tsx` | — |
| LoadingState, EmptyState, ErrorState (with Retry), Unavailable | `ui.tsx` | — |
| ApprovalCard | `pages/Agent.tsx` | busy, error |
| ModelSelect | `pages/Agent.tsx`, reused by Prompt Studio | local/cloud optgroups, location explanation |
| Prompt editor and variables | `pages/PromptStudio.tsx` | missing-variable guard, run busy/error, recent prompts empty |
| History timeline and filters | `pages/Audit.tsx` | loading/empty/error, 25-row cursor pages, exports |
| Models, resource tables and Costs | respective pages | loading/empty/error, expandable metadata, explicit unknown values |
| Settings search and Appearance | `pages/Settings.tsx` | loading/empty/error, persisted theme |

Pages are lazy-loaded. Concurrent identical GET requests share one promise; health also has a 10-second cache. Tabs support left/right arrows, Home/End and a single tab stop.

Not built yet: reusable advanced DataTable, Toast, NotificationCentre, DiffViewer and cost charts. The present timeline uses server cursor paging and ordinary semantic lists/tables, without adding another dependency.
