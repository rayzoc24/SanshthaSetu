# Module 0.5 Design — UI Theme Pass

**Precondition:** Module 0 Definition of Done passes.

## Goal

Apply a government-compliant visual identity (UX4G / GIGW guidelines) across the entire frontend so that every subsequent module inherits it without rework. No backend changes.

## Theme Approach

- Define all design tokens as CSS custom properties in `src/styles/theme.css` (colors, typography scale, spacing, border-radius, shadow).
- Map Tailwind's `theme.extend` to those CSS variables in `tailwind.config.js` so Shadcn components and custom components both consume the same tokens.
- UX4G palette: primary `#003087` (deep government blue), accent `#F47920` (saffron), surface `#F5F5F5`, text `#212121`.
- Typography: system font stack with fallback to `Inter`; heading sizes from UX4G scale.
- No hard-coded hex, `px`, or `rem` values inside component files — reference tokens only.

## Shared Layout

- `AppShell` component: government header bar (logo, portal name, user info, logout), left sidebar (role-aware nav links), main content area, sticky footer with disclaimer.
- Header includes the national emblem placeholder and "AICTE | SanshthaSetu" wordmark.
- Sidebar nav items are derived from the authenticated user's role (Zustand store).
- `ProtectedRoute` wraps all authenticated pages; redirect to `/login` on 401.

## Accessibility Baseline

- Semantic HTML: `<header>`, `<nav>`, `<main>`, `<footer>`, `<aside>`.
- Every interactive element has a visible focus ring (2 px outline, offset 2 px, primary color).
- All color pairs meet WCAG 2.1 AA contrast (4.5:1 for body text, 3:1 for large text).
- Form inputs use `<label htmlFor>` and `aria-describedby` for error messages.
- Images have `alt` text; decorative images have `alt=""`.

## Pages in Scope

- `/login` — updated to theme.
- `/dashboard` (role-aware shell, empty content placeholder for later modules).
- `404` — simple branded page.

## Out of Scope

- No new API endpoints.
- No data tables or forms beyond login.
- Accessibility audit tooling (axe, Lighthouse) run manually; no CI gate added yet.

## Migration Notes

- No DB migration for this module.
- Update `components.json` (Shadcn) CSS variable names to match new tokens if they conflict.
