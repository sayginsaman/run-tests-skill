# Test Catalog

Use this to add `[CODEX]` tests in Phase 3. Pick only what applies to the app type and to the changed files. Changed areas get deep coverage; untouched areas only get a quick regression pass on the main path.

## Contents
1. Always run
2. Web apps and websites
3. Forms and input
4. Auth and accounts
5. Data, persistence and state
6. Desktop apps (Electron, Tauri, native)
7. Mobile apps (simulator / emulator)
8. Marketing and content sites
9. Dashboards and data views
10. AI features (LLM calls)
11. Payments
12. Files, uploads and permissions
13. Accessibility quick pass
14. Picking tests by change type

## 1. Always run
- **T00 Smoke:** app starts, first screen renders, no crash, no blank screen.
- **Console clean:** no uncaught errors or failed network requests in the browser console / app logs during the main flow.
- **Happy path of every changed feature,** end to end, as a new user would do it.
- **Reload / restart:** state that should persist does; state that should reset does.
- **Navigation:** every link or menu item touched by the changes leads somewhere real (no 404, no dead buttons).

## 2. Web apps and websites
- Responsive: test at about 375px (phone), 768px (tablet), and 1440px (desktop). Look for overflow, horizontal scroll, overlapping elements, unreadable text, tap targets that are too small.
- Light and dark mode if the app supports both.
- Browser back/forward and deep links: open a changed route directly by URL.
- Refresh in the middle of a multi-step flow.
- Slow network (devtools throttling "Slow 3G"): loading states appear, no double rendering, no stuck spinners.
- Offline (devtools offline): a clear error, not a silent failure or a white screen.
- 404 page for an unknown route.
- Page title and favicon present on changed pages.

## 3. Forms and input
- Required field empty: blocked with a clear message near the field.
- Invalid formats (email, phone, URL, number out of range).
- Very long input (500+ characters), emoji, non-Latin text (e.g. Turkish characters ç ğ ı ö ş ü), leading/trailing spaces.
- Special characters that break naive code: `' " < > & ; --` and `<script>alert(1)</script>` (should render as text, never execute).
- Double-click submit: only one record created.
- Enter key submits where expected; Tab order is logical.
- Error from the server shows a friendly message and keeps the user's input.

## 4. Auth and accounts
- Sign up with a new test account, log out, log back in.
- Wrong password: generic error, no account enumeration.
- Protected page while logged out: redirected to login, then back to the original page after login.
- Session after reload stays logged in; logout actually clears it (back button does not show private data).
- One user cannot see another user's data (create two test accounts if the feature is per-user).
- Password reset flow up to the point where a real email would be needed.

## 5. Data, persistence and state
- Create, read, update, delete for every entity the changes touch.
- Empty state (no data yet) looks intentional.
- Many items (add 20+ if cheap): lists scroll, paginate or virtualize correctly.
- Sorting and filtering combine correctly and survive reload if they are meant to.
- Two tabs/windows open: changes in one appear (or are handled) in the other.
- Undo / cancel paths do not save.

## 6. Desktop apps (Electron, Tauri, native)
- Launch from the build or dev command; window title and icon correct.
- Resize to small and large; minimum window size respected.
- Close and reopen: settings and data persisted.
- Menus and keyboard shortcuts (Cmd/Ctrl+Q, Cmd/Ctrl+W, copy/paste in inputs).
- OS permission prompts the app raises (files, mic, camera, notifications): grant and confirm the feature then works.
- Multiple monitors / moved window not required unless the change involves windows.
- App does not keep running in the background after quit unless intended.

## 7. Mobile apps (simulator / emulator)
- Cold start, background and resume.
- Portrait and landscape if supported.
- Keyboard does not cover the focused input.
- Permission prompts (location, camera, notifications): allow path and deny path.
- Pull to refresh, swipe gestures, back gesture on Android.
- Small screen device and large screen device.

## 8. Marketing and content sites
- Hero, navigation, footer links, CTAs all work.
- Contact / signup forms submit (to a test endpoint or stop before a real send).
- Images load, no layout shift on load, alt text present on meaningful images.
- Meta title and description on changed pages; Open Graph image if relevant.
- Anchor links scroll to the right section, sticky header does not cover headings.
- Language switcher if the site is multilingual.

## 9. Dashboards and data views
- Numbers match the source data for at least one record you can check by hand.
- Charts render with zero, one and many data points.
- Date range filters, including edge dates and time zones.
- Tables: sort, search, pagination, export if present.
- Loading and error states for each widget.

## 10. AI features (LLM calls)
- Normal prompt returns a sensible result in reasonable time with a loading indicator.
- Empty input and very long input.
- API failure or missing key: friendly error, no raw stack trace or key shown in the UI.
- Streaming output (if any) renders cleanly and can be stopped.
- Output with markdown or code renders safely.

## 11. Payments
- Test mode only, published test cards only (Stripe: `4242 4242 4242 4242` success, `4000 0000 0000 0002` declined).
- Success, decline, and cancel paths; the UI reflects each correctly.
- Never complete a payment with a real card or in live mode. Mark as BLOCKED if test mode is not available.

## 12. Files, uploads and permissions
- Upload a valid file from a test fixtures folder (create one in `.codex-test-runs/fixtures/` if needed).
- Wrong file type, oversized file, empty file.
- Folder picker: grant access to a test folder; confirm the app reads/writes only there.
- Download/export produces a file that opens.
- Drag and drop if supported.

## 13. Accessibility quick pass
- Tab through the changed screens: every control reachable, focus visible, no keyboard trap.
- Buttons and inputs have readable labels.
- Text contrast is clearly readable in both themes.
- Modals close with Escape and return focus.

## 14. Picking tests by change type
| Change in transcript | Add these |
|---|---|
| New page or route | Section 2 responsive + deep link + 404, section 13 |
| New or changed form | Section 3 fully |
| Auth, middleware, session code | Section 4 fully |
| API route, database, state store | Section 5 CRUD + reload + error states |
| Styling, layout, design system | Section 2 responsive + dark mode + section 13 contrast |
| Electron/Tauri/native code | Section 6 |
| Upload, file system, OS integration | Section 12 + permission prompts |
| LLM / AI integration | Section 10 |
| Payment or billing code | Section 11 |
| Refactor with "no behavior change" | Regression pass on every screen that imports the changed files |
