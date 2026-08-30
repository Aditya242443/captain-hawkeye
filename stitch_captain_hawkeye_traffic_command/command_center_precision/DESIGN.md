---
name: Command Center Precision
colors:
  surface: '#faf8ff'
  surface-dim: '#d9d9e4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3fd'
  surface-container: '#ededf8'
  surface-container-high: '#e7e7f2'
  surface-container-highest: '#e1e2ec'
  on-surface: '#191b23'
  on-surface-variant: '#434654'
  inverse-surface: '#2e3038'
  inverse-on-surface: '#f0f0fb'
  outline: '#737685'
  outline-variant: '#c3c6d6'
  surface-tint: '#0c56d0'
  primary: '#003d9b'
  on-primary: '#ffffff'
  primary-container: '#0052cc'
  on-primary-container: '#c4d2ff'
  inverse-primary: '#b2c5ff'
  secondary: '#4c5e83'
  on-secondary: '#ffffff'
  secondary-container: '#bfd2fd'
  on-secondary-container: '#475a7e'
  tertiary: '#7b2600'
  on-tertiary: '#ffffff'
  tertiary-container: '#a33500'
  on-tertiary-container: '#ffc6b2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001848'
  on-primary-fixed-variant: '#0040a2'
  secondary-fixed: '#d7e2ff'
  secondary-fixed-dim: '#b4c7f1'
  on-secondary-fixed: '#041b3c'
  on-secondary-fixed-variant: '#34476a'
  tertiary-fixed: '#ffdbcf'
  tertiary-fixed-dim: '#ffb59b'
  on-tertiary-fixed: '#380d00'
  on-tertiary-fixed-variant: '#812800'
  background: '#faf8ff'
  on-background: '#191b23'
  surface-variant: '#e1e2ec'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-md:
    fontFamily: jetbrainsMono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
---

## Brand & Style

The design system is engineered for high-stakes urban monitoring and data-intensive decision-making. The brand personality is authoritative, vigilant, and hyper-functional, mirroring the reliability of an automated "eye in the sky."

The aesthetic follows a **Modern Corporate Minimalism** approach. It prioritizes information density without clutter, utilizing significant whitespace to ensure that critical traffic alerts and ANPR data are never obscured by decorative elements. The visual language is strictly utility-driven, eschewing trends like glassmorphism or gradients in favor of flat surfaces, crisp borders, and a disciplined "command center" layout that reduces cognitive load for operators.

## Colors

The palette is anchored in professional reliability. 
- **Primary:** Used for focus states, primary actions, and brand identification.
- **Backgrounds:** A distinct separation between the page background (#F4F5F7) and the surface of the cards (#FFFFFF) creates a natural layering effect.
- **Functional Colors:** These are strictly reserved for data visualization and status indicators. Red and Orange denote congestion or violations; Green signifies fluid movement; Light Blue indicates manageable density.
- **Neutral:** Dark Charcoal is used for maximum legibility in primary text, while Mid-Gray handles metadata and secondary information.

## Typography

This design system utilizes **Inter** for all UI elements to ensure maximum clarity and accessibility across varied display resolutions. A secondary technical font, **JetBrains Mono**, is introduced specifically for ANPR plate readouts and technical coordinates to prevent character confusion (e.g., distinguishing '0' from 'O').

Headers use semi-bold weights to anchor dashboard sections, while body text maintains a comfortable 14px-16px base. Labels are frequently uppercased with slight tracking to differentiate them from interactive text.

## Layout & Spacing

The layout follows a **Fixed-Fluid Hybrid Grid**. On desktop, the primary navigation is a fixed left-hand sidebar (240px), while the dashboard content expands fluidly to fill the remaining viewport.

- **Grid:** 12-column system for dashboard widgets. Widgets should span 3, 4, 6, or 12 columns.
- **Rhythm:** A 4px baseline grid ensures vertical consistency. 
- **Margins:** 24px outer page margins, with 16px gutters between modular cards.
- **Responsive:** On tablet, the 12-column grid collapses to 6. On mobile, all widgets stack vertically (1-column), and horizontal navigation transforms into a bottom bar or hamburger menu.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Subtle Ambient Shadows**. 
- **Level 0 (Background):** #F4F5F7 (The base "canvas").
- **Level 1 (Cards/Widgets):** #FFFFFF with a 1px border (#EBECF0) and a soft, low-opacity shadow (Y: 2px, Blur: 4px, Color: rgba(9, 30, 66, 0.08)).
- **Level 2 (Modals/Dropdowns):** Elevated further with a more pronounced shadow (Y: 8px, Blur: 16px, Color: rgba(9, 30, 66, 0.12)).

Interactions (like hovering over a widget) should slightly deepen the shadow rather than changing the surface color, maintaining the dashboard's "flat but tactile" feel.

## Shapes

The design system utilizes a **Rounded** shape language to soften the industrial nature of data monitoring. 
- **Small Elements (Inputs, Buttons):** 4px to 6px radius.
- **Containers (Cards, Widgets):** 8px standard radius.
- **Large Sections (Sidebars, Modals):** 12px radius.

All ANPR plate captures and camera feeds should maintain a 4px radius to feel integrated into the UI.

## Components

### Buttons
- **Primary:** Solid #0052CC background with white text. 4px radius.
- **Secondary:** Ghost style with #0052CC border and text.
- **Status-based:** Solid #DE350B for "Emergency Stop" or "Clear Alert" actions.

### Data Cards
Every dashboard widget must be encapsulated in a white card with an 8px radius. Titles are 14px Semi-bold (#172B4D) with a 1px bottom border separating the header from the content.

### Inputs & Search
Fields use a #FAFBFC light gray fill with a 2px #DFE1E6 border. On focus, the border transitions to #0052CC. For the ANPR search bar, include a clear "magnifying glass" icon and a keyboard shortcut hint (e.g., "CMD+K").

### Status Chips
Pill-shaped indicators (32px height) for traffic density.
- **High:** Light Red background / Dark Red text.
- **Low:** Light Green background / Dark Green text.

### Monitoring Feeds
Camera thumbnails must include a timestamp overlay in the top-right corner using JetBrains Mono 10px, white on a 50% black semi-transparent background.