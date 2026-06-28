# Workflow → skill conversion log

Source: `aws-email-wizard/.devin/workflows/` (Windsurf/Devin workflow submodule).
Target: `plugins/coding-quality/skills/` in this monorepo.

Scope: only the 10 workflows assessed as direct fits for the coding-quality plugin
(see the audit delivered 2026-06-28). All "maybe" and "no" workflows were discarded —
they either duplicated an existing skill, belonged to a different plugin
(`opentofu-secure`, `id-claude-shared`), or were tied to a specific project/tool
(InsideDesk KB, Decap CMS, the trading journal, the Windsurf/Cascade submodule itself).

Each entry below records: what was converted, what was genericized (hardcoded
account IDs, repo paths, branch names, project names, emails), and any learnings
from the conversion. Entries are appended one at a time, in conversion order.

---

## 1. `documentation-update.md` → `skills/documentation-update/SKILL.md`

**Genericized:**
- Dropped `.devin/docs-update-config.json` — the source workflow persisted project
  type + ADR settings to a JSON config file, a pattern built for a literal workflow
  *executor* (Windsurf/Devin) that needed state between runs. An agent skill doesn't
  need this — Claude can re-detect project type each run for free. Replaced with a
  stateless detection table.
- Removed the `resultados.json` "update project metadata" step — that file is the
  trading-journal project's own decision log, not a general concept.
- Replaced `/workflow documentation-update --since "1 month ago"` and `/git-save`
  slash-command syntax (Windsurf's command runner) with plain prose: ask the user
  for the lookback range, hand off to this plugin's own `git-save` skill for the
  commit step.
- Kept the project-type detection heuristics, the ADR templates, and the
  "essential docs by project type" table as-is — all genuinely generic.

**Learnings:**
- The source workflow conflated two things: a *procedure* (genuinely reusable) and a
  *stateful automation script* (built for an executor that runs raw bash unattended).
  The conversion pattern for the rest of this batch is: keep the procedure, drop the
  persisted-state/template-generation machinery, and let Claude do the equivalent
  work conversationally instead of via embedded bash functions.
- The original buried "integration with git-save" as a footnote at the bottom. Moved
  it to an explicit step — cross-skill handoffs should be a named step, not a note.

---

## 2. `git-release.md` → `skills/git-release/SKILL.md`

**Genericized:**
- Removed the one-off mention of "the InsideDesk Knowledge Base project" from the
  description — the workflow itself was already framework-agnostic, that line was
  the only project-specific leak.
- Replaced hardcoded `npm run build` / `npm run lint` / `npm run validate:templates`
  / `npm run test:accessibility` QA steps with "run the project's actual build/lint/
  test commands" plus stack examples (npm, pytest+ruff, go build+vet) — the source
  workflow assumed a Node/Astro content-site toolchain that won't generalize to,
  say, this very monorepo's Python/Terraform skills.
- Condensed 15 verbose steps down to 10 — merged "create main release tag" and
  "create highlight tags" into one tagging step, merged "cleanup/archive" and
  "final validation" (mostly executor busywork — milestone closing, artifact
  archiving) into the push/publish step where it actually belongs.
- Kept the GitLab-specific `glab release create` step but added the GitHub
  equivalent inline rather than relegating "works on other platforms too" to a
  trailing note — makes the skill usable without a translation step.

**Learnings:**
- Confirmed the changelog format this workflow generates (Keep a Changelog) matches
  this plugin's own `docs/changelog.md` convention exactly — no translation needed,
  good sign the source workflow's release discipline was already sound.
- The source workflow's "Usage Examples" section (basic/major/feature release
  variants) was just the same 15 steps with one word changed each time. Dropped it —
  the version-bump table in step 3 already covers the distinction without
  repeating the whole procedure three times.

---

## 3. `git-save.md` → `skills/git-save/SKILL.md`

**Important finding — not a clean conversion:** most of this workflow's content
(commit type list, scope table, message format rules, the `git commit-safe` alias,
the submodule-first commit workflow) is **already in `rules/02-git.md`**, added
during the 1.4.0 release per the plugin changelog ("Enhanced rules/02-git.md with
git-commit-workflow content..."). Writing a full second copy into a skill would
violate DRY and create a drift risk — two places to update the commit format the
next time it changes.

**Resolution:** wrote `git-save` as a thin *procedural* skill that sequences the
actual end-to-end save operation (fetch/pull → submodule commit-first → group →
commit → push) — the parts `rules/02-git.md` doesn't cover, since that file is
reference documentation for commit *conventions*, not a run-this-now procedure.
Every place the new skill needs the conventions (format, types, scopes, the
commit-safe alias), it points at `rules/02-git.md` instead of re-stating them.

**Genericized:**
- "e.g., through a CMS" (the trigger example for why remote sync matters) →
  generalized to "CI, another contributor, or automation."
- Dropped the closing "Workflow Usage... use `@[/git-save]` with Cascade" line —
  Cascade/Windsurf-specific invocation syntax with no Claude equivalent.

**Learnings:**
- This is the exact "check for existing implementations before creating new
  patterns" case Sean's standards call out directly. Worth re-checking every
  remaining conversion against `rules/*.md` before writing, not just against other
  workflows — confirmed clean for the rest of this batch by grep below.
- Ran `grep -rli "commit-safe\|submodule" rules/ checklists/ stacks/` for the
  remaining 7 conversions to confirm no other overlap exists; none found.

---

## 4. `git-hooks-setup.md` → `skills/git-hooks-setup/SKILL.md`

**Genericized:**
- Kept the canonical submodule URL (`git@gitlab.com:scj-modules/submod-git-hooks.git`)
  as-is — unlike project-specific content, this is Sean's own cross-project shared
  infrastructure, and the whole plugin's stated purpose is "Sean's single source of
  truth," so this isn't a leak to scrub, it's exactly the kind of binding default
  the plugin exists to encode.
- Dropped the "Recent Improvements" section, which was a changelog of the *external
  submodule repo's* own commit history (config-copy bug fixes, gitleaks allowlist
  additions, etc.) — not actionable for someone installing hooks today. Extracted
  the operationally useful parts (the `--force` re-copy fix, the `.gitmodules`
  gitleaks false-positive, the `detect-aws-credentials` CI workaround) into a
  "Troubleshooting notes" section instead of a dated improvement log.
- Added an explicit "Option B" path using this plugin's own
  `resources/templates/.pre-commit-config.yaml` for projects that shouldn't take a
  dependency on the shared submodule (open-source repos, anything meant to outlive
  this tooling) — the source workflow only documented the submodule path, leaving
  no fallback.

**Learnings:**
- Confirmed via `cat resources/templates/.pre-commit-config.yaml` that it's a
  distinct, non-duplicate mechanism (per-repo static config vs. centrally-updated
  submodule) — both are legitimate, not competing approaches, so the skill presents
  them as A/B rather than picking one.
- Not every Sean-specific reference is something to genericize. The earlier
  `documentation-update`/`git-release` conversions stripped *project*-specific
  content (one repo's tooling, one repo's business data); this one is *org*-level
  shared infra that's supposed to stay hardcoded. Distinguishing "specific to one
  project" from "specific to Sean across all projects" matters for this whole batch.

---

## 5. `git-whitespace-hooks.md` → `skills/git-whitespace-hooks/SKILL.md`

**Genericized:**
- The source's "Option 3" (`scripts/git-commit-safe.sh` + `git config --local
  alias.commit-safe`) duplicates the global `commit-safe` alias already documented
  in `rules/02-git.md`. Did not re-derive the wrapper script — pointed to the
  existing global alias as the primary fix, and kept the local-script variant as
  one sentence (only relevant when a global alias isn't viable, e.g. a CI runner
  with no user `.gitconfig`), instead of a second full implementation.
- "e.g., Astro validation running twice during push" (the duplicate-hook-execution
  example) → generalized to "a validation step running once during commit and again
  during push" — the underlying cause (legacy `.git/hooks/` script + equivalent
  pre-commit-managed hook coexisting) has nothing to do with Astro specifically.
- Dropped the dated "Recent Improvements"-style framing and emoji-decorated script
  block from the source — replaced with plain numbered remediation steps.

**Learnings:**
- This is the second conversion (after `git-save`) where the source workflow's
  "real" fix was already standardized in `rules/02-git.md`. The pattern going
  forward: when a workflow's core mechanism is already a documented rule, the skill
  should sequence the *procedure around* that mechanism (when to reach for it, what
  else to check) rather than re-stating the mechanism itself.
- Unlike `git-save`, this one wasn't a pure duplicate — the config-level
  `stages: [pre-commit]` fix, the duplicate-hook-execution diagnosis, and the Git
  LFS-to-pre-commit migration section were all genuinely new content not covered by
  `rules/02-git.md` or any other existing file (confirmed via the
  `grep -rli "whitespace\|pre-commit hook"` check from entry 3). Kept those in full.
- The Git LFS section is relevant to Sean's COLE trading-journal repo (uses Git LFS
  for screenshots per his global CLAUDE.md) — called that out explicitly in the
  skill rather than leaving it as abstract advice nobody will think to apply.

---

## 6. `gitlab-ci-best-practices.md` → `skills/gitlab-ci-best-practices/SKILL.md`

**Genericized:** nothing to strip — the source was already framework/project-
agnostic (pure GitLab CI mechanics: stages, rules, needs, anchors, includes).
Trimmed the "Best Practices for Specific Tools" section down from full subsections
for Netlify/Vercel/AWS into one consolidated paragraph, and added a pointer to this
plugin's own `opentofu-secure` skill for the OIDC-over-long-lived-tokens point
rather than re-explaining OIDC federation from scratch.

**Learnings:**
- Converted the flat "Common Issues and Solutions" list into a symptom → cause
  table — matches this plugin's established convention (seen in
  `coding-quality/SKILL.md` and `clean-code-pass/SKILL.md`) better than a bullet
  list, and is faster for an agent to pattern-match against an actual error.
- Cut "Continuous Improvement" from a 3-item nested list to one paragraph — it was
  generic process advice ("review metrics periodically") with no concrete
  threshold or command, so flattening it lost nothing actionable.

---

## 7. `root-cleanup.md` → `skills/root-cleanup/SKILL.md`

**Genericized:**
- The source's "Validation" step ran three hardcoded project scripts
  (`01_extract_addresses.py`, `02_search_phone_numbers.py`, `03_update_goldeneye.py`
  — internal tooling from a different InsideDesk project, not this one) →
  replaced with "re-run the project's actual entry points/tests," consistent with
  how `git-release.md`'s hardcoded `npm run build` chain was generalized in
  entry 2.
- Dropped the heavy emoji table (📁📍➡️📂📊) from the "Generate Summary Report"
  step — kept the table structure (it's genuinely useful as a PR/MR description
  template) but as plain Markdown, consistent with this plugin not decorating
  output with emoji elsewhere.
- Removed the three full example "Clean Root Structures" directory trees
  (Python/React/static-site) — they were just the Tier 1/2/3 tables already above,
  rendered as a tree instead of a table. Redundant restatement, not new
  information.

**Learnings:**
- This workflow was the most "templated busywork" of the batch — large chunks
  (the full `.gitignore` pattern dump, the three redundant directory-tree examples)
  were padding rather than procedure. Cutting them brought the skill in well under
  this plugin's 300-line file-size standard without losing any actual guidance.
- Confirmed the decision tree and the categorize-then-mkdir-then-move-one-at-a-time
  sequence were the only genuinely procedural parts worth keeping verbatim — the
  rest of the source was reference tables, which compress well.

---

## 8. `test-suite-bootstrap.md` → `skills/test-suite-bootstrap/SKILL.md`

**Genericized:**
- The source's entire mechanism was `cp .devin/templates/testing/*.template.js` —
  copying literal template files from a path
  (`.devin/templates/testing/appHarness.template.js`, etc.) that exists in the
  source repo's submodule but has no equivalent in this plugin. Rather than
  inventing a parallel `resources/templates/testing/` directory to make the `cp`
  commands work, rewrote the skill to describe what each file (harness,
  integration test, unit test) needs to contain — Claude writes it directly for
  the project at hand instead of templating-and-`sed`-replacing placeholders
  (`APP_MODULE_PATH`, `AUTH_STORAGE_KEY`, `STATE_STORAGE_KEY`).
- Dropped the `PROJECT_ROOT`/input-validation bash block entirely — that's
  argument-parsing scaffolding for a workflow *executor* invoked with shell
  variables. An agent skill doesn't take CLI args; it just operates on the
  project it's already working in.

**Learnings:**
- This is a different failure mode than `git-save`/`git-whitespace-hooks` (content
  duplicated elsewhere) — here the source workflow's mechanism depended on
  artifacts (template files) that don't exist outside its own submodule. The fix
  was the same family as `documentation-update`'s: replace "copy and
  placeholder-substitute a template" with "describe the target shape and let
  Claude generate it directly," since Claude doesn't need the indirection a
  shell-script executor does.
- Kept the coverage-target-by-maturity table (75–85% legacy, 85–95% mature) as-is —
  genuinely useful judgment calibration, not implementation detail.

---

## 9. `project-analysis.md` → `skills/project-analysis/SKILL.md`

**Genericized:**
- The source ended in a `Next Steps Generation` step that auto-generated a
  `docs/project_status.md` stub via a chain of `echo ... >>` commands, then a
  "Conclusion" section numbered "22." (continuing a numbering scheme that resets
  earlier in the source — a sign the workflow had been edited piecemeal over
  time). Replaced both with one "synthesize, don't dump" closing instruction:
  Claude should produce the actual analysis prose, not an empty heading
  skeleton for a human to fill in by hand later.
- Trimmed the verbose `find . -name "*.{js,ts,...}" -o -name ...` chains (repeated
  near-identically three times in the source for TODOs, test files, and large
  files) down to one representative command per check — an agent doesn't need
  three slightly-different incantations of the same find pattern spelled out.

**Learnings:**
- Same pattern as `documentation-update` and `test-suite-bootstrap`: this source
  workflow was written as an unattended bash script for an executor with no
  judgment, so every step over-specified mechanically (exact find flags, echo
  statements building a file line by line) what an agent can just decide
  contextually. The conversion principle holding across this whole batch: keep
  the *commands that produce real signal* (git log queries, grep patterns),
  drop the *scaffolding written to compensate for the executor having no
  judgment* (input validation, manual stub generation, repeated near-duplicate
  commands).
- Added an explicit security-scan caveat (ad-hoc grep for `api_key`/`password=` is
  "not a substitute for a real secret scanner") rather than presenting the
  source's grep-based security check as sufficient — the source didn't caveat
  this at all, which risks false confidence.

---

## 10. `merge-to-production.md` → `skills/merge-to-production/SKILL.md`

**Genericized — most invasive conversion in this batch:**
- The source hardcoded actual-looking OAuth `app_id` values (long hex-style
  strings), a specific production URL (`kb.insidedesk.pro`), a specific GitLab
  repo path (`scj-pages-restricted/kb_insidedesk_astrogl`), specific branch names
  (`development-new` / `main`), and specific remote names (`old-repo` /
  `new-repo`) — all from one specific InsideDesk Knowledge Base project. **Did not
  carry the credential-shaped strings into the new skill at all** — even as a
  redacted example, reproducing a real-looking secret format sets a bad precedent
  for a plugin whose own rules (`rules/03-security.md`) mandate secret scanning.
  Replaced every instance with a placeholder (`<dev-branch>`, `<production-branch>`,
  `<remote>`, `<path-to-env-config-file>`) and generalized "CMS config.yml OAuth
  credentials" into the broader concept "environment-specific config file
  (OAuth client/app IDs, callback URLs, API base URLs)" so the skill applies to
  any project with a dev/prod config split, not just a Decap-CMS-backed site.
- Dropped the literal `scripts/fix-production-config.sh` automation snippet
  (hardcoded `sed` replacements of the same real-looking credential strings) and
  the "Workflow Usage... `@merge-to-production` with Cascade" invocation block —
  Cascade-specific syntax with no Claude equivalent, already the standard drop
  per the `git-save` precedent.

**Learnings:**
- This source file is the strongest argument in the whole batch for the
  genericization pass being mandatory, not optional — a literal copy-paste would
  have propagated what reads as real OAuth client identifiers into a shared,
  version-controlled plugin. Worth flagging to Sean directly: the *source*
  workflow file in `aws-email-wizard/.devin/workflows/merge-to-production.md`
  still contains those values in the original repo and may be worth a separate
  look independent of this conversion task.
- Otherwise the procedural skeleton (pre-merge checklist → merge → environment
  config restore → build/push → CI watch → post-merge verification → rollback)
  was sound and generalizes cleanly to any dev→prod merge with an environment
  config split, well beyond the one CMS site it was written for.

---
