# Guided Applicant Step Rail — Design QA

## Comparison target

- Source visual truth: `/Users/willexm1/.codex/generated_images/019fe3d0-9f72-7221-a0d5-f72552572bb0/exec-4c4be098-e4c4-4957-aa59-cebde66f9d75.png`
- Implementation: `http://127.0.0.1:8000/admissions/ADM-2026-00004` as authenticated draft applicant.
- Desktop capture: `/private/tmp/college-application-option-2-full.png`.
- Mobile capture: `/private/tmp/college-application-option-2-mobile.png`.
- Full-view comparison: `/private/tmp/college-application-option-2-comparison.png`.

The source is 1487×1058 pixels. The desktop route was evaluated at a 1440×1024 CSS-pixel viewport, DPR 1; its full-page capture is 1440×1177 pixels. The comparison normalizes each source/implementation top content region to 720×512 pixels before placing them side by side. The mobile route was evaluated at 390×844 CSS pixels, DPR 1; its full-page capture is 390×1674 pixels.

## State and interactions tested

- Draft `ADM-2026-00004`, step 2 of 4, with step 1 saved and complete.
- The desktop rail changed the saved first step to a green checkmark, the active step to `In progress`, and future steps to `Not started`.
- `Save and exit` saved the draft through the existing endpoint and returned to `/admissions`, where the same draft showed an updated `Last saved` timestamp and `Open application` action.
- Browser console error check: no application errors.
- At 390px, the rail becomes a horizontally scrollable strip while the form fields remain single-column and all primary actions remain visible.

## Findings

No actionable P0, P1, or P2 differences remain.

### Required fidelity surfaces

- **Fonts and typography:** The implementation uses the installed Frappe system typography. Its heading hierarchy, field labels, muted explanatory text, and compact status text match the source's restrained, high-legibility hierarchy. The actual programme title wraps only at the narrow breakpoint, where it remains readable.
- **Spacing and layout rhythm:** The implementation keeps the source's broad header, thin progress rule, narrow vertical step rail, and spacious form panel. It intentionally retains Frappe's portal sidebar and real configured field density; both are product constraints rather than visual regressions.
- **Colors and visual tokens:** Neutral surfaces, dark primary action, subdued borders, amber draft indicator, and green saved/completed states use the installed Frappe token system. No new gradient, shadow system, or brand palette was introduced.
- **Image quality and asset fidelity:** Neither the source nor implementation requires a product image, illustration, logo, or custom icon asset for this workspace. The completed-step checkmark uses the framework-native text treatment rather than adding an unrelated asset.
- **Copy and content:** The actual configured application fields replace the mock's generic education examples, while preserving the source's purpose: clearly named steps, visible saved state, return-later reassurance, and explicit save/continue actions.

## Comparison history

1. Initial desktop review found that the label changed to `Completed`, but the marker could not receive the matching state because the state attribute was only assigned to the nested label.
   - Fix: assign the same `data-step-state` to the step button, which owns the marker selector.
   - Evidence: the final desktop capture shows the green checkmark for `Your details` and the active state for `Application details`.

## Follow-up polish

- [P3] At very narrow widths, the horizontal step strip intentionally clips the next step to signal that it can scroll. A later mobile-specific refinement could add a subtle scroll affordance if user testing shows applicants miss it.

## Final result

final result: passed
