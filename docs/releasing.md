# Releasing

Releases are automated with GitHub Actions. Nothing has to be built, tagged or uploaded from a
developer machine.

## Release process

1. Run the **Release - bump version & changelog** workflow (`workflow_dispatch`) and pick the
   increment type. It opens a `bump: release vX.Y.Z` pull request that updates `CHANGELOG.md`,
   `.cz.yaml` and `setup.py`.
2. Merge that pull request. **Release - tag & publish** detects the `bump: release` commit on
   `main` and creates the `vX.Y.Z` tag from the version in `.cz.yaml`.
3. The same workflow run then builds the sdist and wheel, publishes them to PyPI via trusted
   publishing (environment `pypi`, no API token) and creates the GitHub release with the changelog
   section for that version.

## Increment types

`auto` lets commitizen determine the increment from the commit messages. Pass `PATCH`, `MINOR` or
`MAJOR` explicitly to override it.

`release-candidate` (from `main` or a `patch-release-*` branch) creates `X.Y.Z-rc.N`, and
`experimental` (only from an `experimental-*` branch) creates `X.Y.Z-alpha.N`. Both are published
as GitHub pre-releases.

## Workflows and actions

| File | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/pr-checks.yaml` | pull request or explicit release-PR dispatch | Validate the conventional commit messages |
| `.github/workflows/release-changelog.yaml` | manual | Version bump, changelog, release PR |
| `.github/workflows/release-publish.yaml` | push to `main`, `patch-release-*` or `experimental-*` | Tag the release commit, build, publish to PyPI, create the GitHub release |

The workflow steps live in local composite actions:

| Action | Purpose |
| --- | --- |
| `.github/actions/validate-conventional-commits` | Run `cz check` against the pull request title and commits |
| `.github/actions/generate-changelog` | Run `cz bump --files-only --changelog` and open the release pull request |
| `.github/actions/tag` | Tag a `bump: release` commit with the version from `.cz.yaml` |

Both the validation and the changelog action install the commitizen plugin from the checkout
(`pip install .`), so the repository validates and releases itself with the code under review: a
change that breaks commit parsing or changelog rendering breaks its own pipeline instead of shipping
silently.

Third-party actions are pinned by commit SHA so that Renovate can propose updates.

## Required configuration

* PyPI trusted publisher for the project: repository `apheris/cz-github-jira-conventional`,
  workflow `release-publish.yaml`, environment `pypi`
  (see the [PyPI docs](https://docs.pypi.org/trusted-publishers/)).
* A GitHub environment named `pypi`. Add required reviewers there if the publish step should be
  manually approved.

No Actions secrets are needed: PyPI is reached through OIDC, and the bump pull request, the tag and
the GitHub release are created with the built-in `GITHUB_TOKEN`. Because pull requests created with
that token do not emit `pull_request` events, the changelog action explicitly dispatches
`pr-checks.yaml` for the generated release branch.

## Notes on signing and triggers

* The bump commit is signed and shows as **Verified**. It is created through the GraphQL
  `createCommitOnBranch` API, which GitHub signs with its own GPG key. The author is
  `github-actions[bot]`.
* The annotated tag object is created through the REST API, which does not GPG-sign tag objects.
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
