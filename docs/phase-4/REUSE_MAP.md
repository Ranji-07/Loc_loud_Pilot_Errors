# Reuse map (UI pieces)

Checked 2026-11-24 through the GitHub API. Phase 0 research covers the larger systems (OpenHands, Continue, Cline, Open WebUI and others).

| Repo | Module | Licence | Last commit (verified) | Integration | Decision |
|---|---|---|---|---|---|
| lucide-icons/lucide | `lucide-react` 1.78 | ISC (npm metadata; GitHub reports NOASSERTION) | 2026-11-23 | npm dependency, tree-shaken icons | **Used** (the single icon set) |
| pacocoursey/cmdk | command menu | MIT | 2025-10-29 | npm | Not used: about 13 months without commits; a native `<dialog>` palette (~90 lines) covers the need |
| shadcn-ui/ui | copy-in components | MIT | 2026-11-23 | CLI copies source | Deferred: adopt per component (Dropdown, Popover, Toast) when a screen needs one, instead of initialising the whole kit now |
| radix-ui/primitives | accessible primitives | MIT | 2026-10-14 | npm (via shadcn) | Deferred with shadcn |
| TanStack/table | headless data table | MIT | 2026-11-24 | npm | Planned for History and approvals paging (step 8) |
| Aeolun/react-diff-viewer-continued | diff viewer | MIT (to verify) | not checked yet (old repo URL returned 404) | npm | Candidate for Approvals diff preview (step 8); verify before adding |
