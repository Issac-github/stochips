# StoChips Frontend Design System

## Style

StoChips uses **Minimalist Modern** as its single frontend design language.

Core principle: **clarity through structure, character through bold detail**. The UI should feel professional, data-focused, premium, and alive. Use restraint in the number of elements, but execute the important elements with confident typography, Electric Blue accents, elevated surfaces, and purposeful motion.

## Tokens

Use the centralized CSS variables in `src/renderer/src/assets/style/global.css`.

- `background`: `#FAFAFA`
- `foreground`: `#0F172A`
- `card`: `#FFFFFF`
- `muted`: `#F1F5F9`
- `muted-foreground`: `#64748B`
- `accent`: `#0052FF`
- `accent-secondary`: `#4D7CFF`
- `border`: `#E2E8F0`

Typography:

- Display headings: `Calistoga, Georgia, serif` via `.font-display`
- UI and body: `Inter, system-ui, sans-serif`
- Labels and technical badges: `JetBrains Mono, monospace` via `.font-mono`

Effects:

- Primary gradient: `.accent-gradient`
- Gradient text: `.gradient-text`
- Focus state: `.focus-ring`
- Elevated surfaces: `.surface-card`, `.surface-panel`, `.surface-chip`
- Dark texture: `.dot-pattern`

## Component Rules

- Buttons use the Electric Blue gradient for primary actions, `rounded-xl`, visible focus rings, and hover lift with accent-tinted shadows.
- Cards use white backgrounds, subtle borders, `rounded-xl` or `rounded-2xl`, and layered shadows for depth.
- Inputs use white or subtle muted backgrounds, borders, `rounded-xl`, and accent focus states.
- Section labels use pill badges with an accent dot, mono uppercase text, and optional pulse animation.
- Data-heavy surfaces should stay calm and readable. Use accent color sparingly for key actions, active states, live indicators, and highlighted words.
- Inverted contrast sections are allowed for navigation, stats, or spotlight areas. Use deep slate backgrounds with subtle dot texture.

## Avoid

- Do not reintroduce Ant Design or AntD styling patterns.
- Do not use the old gold theme.
- Do not switch to full flat/poster design globally.
- Do not use large multicolor palettes where the Electric Blue accent should carry emphasis.
- Do not remove focus indicators.
- Do not create one-off colors or shadows when an existing token or utility class fits.

## Current Architecture

The frontend is Electron + React + TypeScript with Tailwind 4 and local shadcn-style primitives:

- `src/renderer/src/components/ui/*`: reusable UI primitives
- `src/renderer/src/components/shared/*`: app-level shared components
- `src/renderer/src/components/layout/MainLayout.tsx`: app shell and navigation
- `src/renderer/src/assets/style/global.css`: tokens, fonts, and global utilities

When adding or redesigning UI, update primitives or shared components first, then compose pages from those pieces.
