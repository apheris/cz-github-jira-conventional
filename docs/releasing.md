# Releasing

Releases are automated with GitHub Actions. Nothing has to be built, tagged or uploaded from a
developer machine.

## Release process

1. Run the **Release - bump version & changelog** workflow (`workflow_dispatch`) from protected
   `main` or a protected `patch-release-*` branch and pick the increment type. The job checks the
   workflow source ref separately from the selected release base because `$/` actions come from
   the workflow ref. It opens a `bump: release vX.Y.Z` pull request that updates `CHANGELOG.md`,
   `.cz.yaml` and `setup.py`.
2. Squash-merge that pull request, preserving its `bump: release vX.Y.Z` title (GitHub's appended
   `(#123)` suffix is supported). **Release - tag & publish** detects that exact release header on
   protected `main` or `patch-release-*` branches and checks that its version matches both `.cz.yaml`
   and `setup.py` before creating the `vX.Y.Z` tag. Other `bump:` commits do not publish anything.
3. The same workflow run then builds the sdist and wheel, publishes them to PyPI via trusted
   publishing (environment `pypi`, no API token) and creates the GitHub release with the changelog
   section for that version.

## Increment types

`auto` lets commitizen determine the increment from the commit messages. Pass `PATCH`, `MINOR` or
`MAJOR` explicitly to override it.

`release-candidate` creates `X.Y.Z-rc.N` and is published as a GitHub pre-release.
All increment types must target `main` or a protected `patch-release-*` branch. The changelog action
verifies the selected branch's protection through the GitHub API before checking out or installing
repository code, then pins checkout and the release PR's starting commit to that verified SHA.
Unsupported, unprotected, or inaccessible base branches are rejected before changes are generated.
Experimental/alpha releases are not supported.

## Workflows and actions

| File | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/pr-checks.yaml` | pull request or explicit release-PR dispatch | Run pytest and validate the conventional commit messages |
| `.github/workflows/release-changelog.yaml` | manual | Version bump, changelog, release PR |
| `.github/workflows/release-publish.yaml` | push to protected `main` or `patch-release-*` | Tag the release commit, build, publish to PyPI, create the GitHub release |

The workflow steps live in local composite actions:

| Action | Purpose |
| --- | --- |
| `.github/actions/validate-conventional-commits` | Run `cz check` against the pull request title and commits |
| `.github/actions/generate-changelog` | Run `cz bump --files-only --changelog` and open the release pull request |
| `.github/actions/tag` | Tag a `bump: release` commit with the version from `.cz.yaml` |

Both the validation and the changelog action install the commitizen plugin from the checkout
(`python -m pip install -r requirements.txt .`), so the repository validates and releases itself
with the code under review. Python is selected from `.python-version` everywhere, and dependencies
(including Commitizen) are pinned once in `requirements.txt` for tests, validation and releases.

Same-repository actions use `$/` references, resolving to the workflow's commit without a preliminary
checkout. Third-party actions are pinned by commit SHA for reproducibility; this repository does not
currently have Renovate, so those pins need manual updates.

## Required configuration

Complete these prerequisites before the first automated release:

* Configure a trusted publisher on the existing `cz-github-jira-conventional` PyPI project:
  repository `apheris/cz-github-jira-conventional`, workflow `release-publish.yaml`, environment
  `pypi` (see the [PyPI docs](https://docs.pypi.org/trusted-publishers/)). This authorizes the matching
  workflow to publish via OIDC; no separate Apheris PyPI maintainer/owner account is required.
  PyPI project-management access is a separate administrative concern: trusted publishing does not
  add or transfer project maintainers, and granting that access is not a release prerequisite.
* Protect `main` and `patch-release-*` with rules requiring reviewed pull requests and passing PR
  checks before merge. The changelog job and publishing workflow refuse unprotected workflow refs.
  Job-level guards are defense in depth, not a substitute for server-side branch protection:
  a writer can edit a workflow on their own branch, including its guards.
* Create the GitHub environment `pypi` and set **Deployment branches and tags** to **Protected
  branches only**. This environment restriction is mandatory: a workflow-level ref check alone
  cannot prevent a writer from changing the workflow on an unprotected branch. Keep this restriction
  in place even if required reviewers are also configured as an additional manual approval gate.

No Actions secrets are needed: PyPI is reached through OIDC, and the bump pull request, the tag and
the GitHub release are created with the built-in `GITHUB_TOKEN`. Because pull requests created with
that token do not emit `pull_request` events, the changelog action explicitly dispatches
`pr-checks.yaml` for the generated release branch.

## Notes on signing and triggers

* The bump commit is signed and shows as **Verified**. It is created through the GraphQL
  `createCommitOnBranch` API, which GitHub signs with its own GPG key. The author is
  `github-actions[bot]`.
* The annotated tag object is created through the REST API, which does not GPG-sign tag objects.
* Tag creation is retry-safe: an existing annotated or lightweight tag is reused only if it resolves
  to the release commit. A tag pointing elsewhere fails the job and is never moved or deleted.
  This allows retries past the tagging step; publishing an already uploaded PyPI version may still
  require rerunning only the failed jobs rather than the entire workflow.
* Tags created with `GITHUB_TOKEN` do not trigger workflows. Tagging, building, publishing and the
  GitHub release therefore run as chained jobs in a single `release-publish.yaml` run rather than
  being split across a tag-push trigger.

## Manual fallback

Only needed if the workflows are unavailable:

```bash
cz bump --changelog          # bumps .cz.yaml + setup.py, writes CHANGELOG.md, creates the tag
python -m build              # sdist + wheel into dist/
python -m twine upload dist/*
```

`twine` needs a PyPI API token (`__token__` as the username, `pypi-…` as the password) from
<https://pypi.org/manage/account/>.
