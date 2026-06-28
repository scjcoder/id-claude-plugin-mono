---
name: git-release
description: >
  Comprehensive release workflow: pre-release QA, semantic version bump, changelog
  generation from git history, top-highlight identification, annotated release tags
  plus lightweight highlight tags, and a documented rollback path. Use this skill
  when the user asks to "cut a release", "tag a release", "bump the version", or
  prepare release notes. GitLab-oriented (GitLab Releases, `glab` CLI) but adapts to
  any Git platform — swap the GitLab-specific steps for the equivalent GitHub/other
  command.
---

# Git release

Turns a clean branch into a tagged, documented release with minimal guesswork about
what changed and why.

## 1. Validate branch state

```bash
git status                              # must be clean
git branch --show-current
git fetch origin
git log --oneline origin/<branch>..HEAD # anything here? sync before releasing
```

## 2. Run QA

Run the project's actual build/lint/test commands — don't assume a stack. Typical
examples: `npm run build && npm run lint && npm test`, `pytest && ruff check .`,
`go build ./... && go vet ./...`. All must pass before continuing.

## 3. Determine the version number

```bash
git describe --tags --abbrev=0          # last release tag
git log --oneline <last-tag>..HEAD      # what's changed since
```

Apply semantic versioning:

| Bump | When |
|------|------|
| MAJOR | Breaking changes |
| MINOR | New features, non-breaking improvements |
| PATCH | Bug fixes, docs, minor improvements |

Update the version field wherever the project declares it (`package.json`,
`pyproject.toml`, `Cargo.toml`, a `VERSION` file, etc.) and anywhere else it's
referenced — grep for stray hardcoded version strings before tagging.

## 4. Generate the changelog

```bash
git log --since="<last-tag-date>" --pretty=format:"%h %s" --no-merges
git log --since="<last-tag-date>" --grep="feat:" --oneline
git log --since="<last-tag-date>" --grep="fix:" --oneline
```

Categorize by conventional-commit prefix, rewrite technical messages into
user-facing language, and append a new section to `docs/changelog.md` (or
`CHANGELOG.md`) using Keep a Changelog format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...

### Security
- ...
```

## 5. Pick the top highlights

From the categorized changelog, select 1–3 changes with the highest user impact
(major feature, critical fix, or notable improvement). Write a 1–2 sentence,
user-benefit-framed summary for each — these become both the release notes intro
and the highlight tags in step 7.

## 6. Commit the release prep

```bash
git add <version-file> docs/changelog.md README.md docs/
git commit -m "release: prepare version X.Y.Z

- Update version to X.Y.Z
- Update changelog
- Update docs for new features

Highlights:
- <highlight 1>
- <highlight 2>"
```

## 7. Tag the release

Annotated tag for the release itself, lightweight tags for each highlight so they're
individually addressable in the history:

```bash
git tag -a vX.Y.Z -m "Release X.Y.Z

<release notes from step 8>

Built from commit: $(git rev-parse HEAD)
Release date: $(date +%Y-%m-%d)"

git tag vX.Y.Z-<highlight-slug> -m "Feature: <description>

Part of release X.Y.Z"
```

## 8. Write release notes

```markdown
# Release X.Y.Z

## Overview
<purpose and impact of this release>

## Key changes
- <highlight 1>
- <highlight 2>

## Breaking changes
<migration guidance, or "None">

## Known issues
<unresolved issues, or "None">
```

## 9. Push and publish

```bash
git push origin <branch>
git push origin --tags
```

Then, on GitLab:

```bash
glab release create vX.Y.Z --notes "<release notes from step 8>"
```

(GitHub equivalent: `gh release create vX.Y.Z --notes "..."`.) Verify tags and the
release page render correctly, and confirm CI/CD picked up the tag if a pipeline is
wired to it.

## 10. Rollback path

Document this before you need it, not after:

```bash
git log --oneline -10                   # find the problematic commit
git checkout -b hotfix/vX.Y.Z+1
# fix, test, tag as a PATCH release, deploy
```

## Checklist

- [ ] Working tree clean, branch synced with remote
- [ ] Build/lint/test all green
- [ ] Version bumped consistently everywhere it's referenced
- [ ] Changelog updated in Keep a Changelog format
- [ ] Release commit created, pre-commit hooks passed
- [ ] Annotated release tag + highlight tags created
- [ ] Pushed commits and tags
- [ ] Release notes published, links verified
- [ ] Rollback path is known before announcing the release
