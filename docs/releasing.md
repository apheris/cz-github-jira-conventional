# Releasing

Releases are automated with the shared actions from
[apheris/github-actions](https://github.com/apheris/github-actions).

## Release process

1. Run the **Release - bump version & changelog** workflow (`workflow_dispatch`) and pick the
   increment type. It runs the Aikido release gate and then opens a `bump: release vX.Y.Z` pull
   request that updates `CHANGELOG.md`, `.cz.yaml` and `setup.py`.
2. Merge that pull request. **Release - tag & publish** then creates the `vX.Y.Z` tag from the
   version in `.cz.yaml`.
3. The tag push builds the sdist and wheel, publishes them to PyPI via trusted publishing
   (environment `pypi`, no API token) and creates the GitHub release with the changelog section
   for that version.

Nothing has to be built, tagged or uploaded from a developer machine.

## Increment types

`auto` lets commitizen determine the increment from the commit messages. Note that the shared
action promotes an auto-detected `PATCH` on `main` to `MINOR`, so that patch releases can be cut
from `patch-release-*` branches independently of `main`. Pass `PATCH`, `MINOR` or `MAJOR`
explicitly to override this.

`release-candidate` (from `main` or a `patch-release-*` branch) creates `X.Y.Z-rc.N`, and
`experimental` (only from an `experimental-*` branch) creates `X.Y.Z-alpha.N`. Both are published
as GitHub pre-releases.

## Workflows

| File | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/pr-checks.yaml` | pull request | Validate the conventional commit messages |
| `.github/workflows/release-changelog.yaml` | manual | Release gate, version bump, changelog, release PR |
| `.github/workflows/release-publish.yaml` | push to `main`, push of `v*` tag | Tag the release commit, build, publish to PyPI, create the GitHub release |

The shared actions are pinned by commit SHA so that Renovate can propose updates.

## Required configuration

* PyPI trusted publisher for the project: repository `apheris/cz_github_jira_conventional`,
  workflow `release-publish.yaml`, environment `pypi`
  (see the [PyPI docs](https://docs.pypi.org/trusted-publishers/)).
* A GitHub environment named `pypi`. Add required reviewers there if the publish step should be
  manually approved.
* Organizational secrets available to this repository:
  * `RELEASER_APHERIS_APP_ID` and `RELEASER_APHERIS_APP_PRIVATE_KEY` — used to open the release PR
    and to create the tag. The tag must be created with the app token, because tags created with
    the default `GITHUB_TOKEN` do not trigger the publish workflow.
  * `AIKIDO_CLIENT_API_KEY` — used by the release gate.

## Note on bootstrapping

`generate-changelog/python-commitizen` installs `cz_github_jira_conventional` from PyPI, so this
repository is released using its own previously released version. If a release changes the commit
parsing or changelog rendering, bump the `cz-github-jira-conventional-version` input in
`.github/workflows/release-changelog.yaml` afterwards to pick it up.

## Manual fallback

Only needed if the workflows are unavailable:

```bash
cz bump --changelog          # bumps .cz.yaml + setup.py, writes CHANGELOG.md, creates the tag
python -m build              # sdist + wheel into dist/
python -m twine upload dist/*
```

`twine` needs a PyPI API token (`__token__` as the username, `pypi-…` as the password) from
<https://pypi.org/manage/account/>.
