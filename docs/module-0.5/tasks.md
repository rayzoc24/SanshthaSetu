# Module 0.5 Tasks — UI Theme Pass

**Precondition:** Module 0 Definition of Done passes.

---

### Task 1 — Design token foundation
Define CSS custom properties for the UX4G palette, typography scale, and spacing in `src/styles/theme.css`.
Wire `tailwind.config.js` `theme.extend` to those variables.
Deliverable: `theme.css` + updated `tailwind.config.js`.
AC: `npm run build` succeeds; no hard-coded hex values remain in any component file.

### Task 2 — AppShell component
Build `src/components/AppShell.tsx`: government header bar, role-aware sidebar nav (from Zustand store), main content slot, sticky footer.
Deliverable: `AppShell.tsx`; `ProtectedRoute` wraps it.
AC: Navigating to `/dashboard` as any role shows the shell; unauthenticated redirect hits `/login`.

### Task 3 — Theme login page
Restyle `/login` using AppShell-free layout and the new tokens; add the AICTE wordmark placeholder.
Deliverable: updated `LoginPage.tsx`.
AC: Login page renders without hard-coded colors; tokens visually match UX4G palette.

### Task 4 — Role-aware dashboard shell
Implement `/dashboard` as an empty AppShell page; sidebar links differ by role (College Admin, Main Admin, Officer stubs).
Deliverable: updated `DashboardPage.tsx` + sidebar nav config.
AC: Each role sees only its own nav items; no 403 is triggered by page load.

### Task 5 — 404 and error boundary
Add a branded `NotFoundPage.tsx` and a React error boundary wrapping the router.
Deliverable: `NotFoundPage.tsx`, `ErrorBoundary.tsx`.
AC: Navigating to `/nonexistent` shows the 404 page; a thrown render error shows the error boundary, not a blank screen.

### Task 6 — Accessibility baseline audit
Run Lighthouse / axe-core in dev mode on login and dashboard; fix all critical (P1) violations.
Deliverable: fixes committed; no new accessibility violations introduced.
AC: No axe-core critical issues on `/login` and `/dashboard`; all focus rings visible; contrast ratios pass AA.

---

## Definition of Done

- [ ] `npm run build` passes with zero errors or hard-coded color/spacing values in components.
- [ ] AppShell renders correctly for every role; sidebar is role-scoped.
- [ ] UX4G tokens applied site-wide via CSS variables; no inline styles.
- [ ] Accessibility: no axe-core critical violations on login and dashboard pages.
- [ ] All focus rings visible; form labels linked to inputs.
- [ ] `ProtectedRoute` redirects unauthenticated users to `/login`.

## Deployment Checkpoint

Deploy the updated frontend to Vercel. Verify the themed login and dashboard load on the live URL with no console errors.
