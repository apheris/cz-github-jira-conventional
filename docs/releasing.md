# Releasing

Releases are automated with GitHub Actions, using local copies of the shared actions from
[apheris/github-actions](https://github.com/apheris/github-actions).

## Release process

1. Run the **Release - bump version & changelog** workflow (`workflow_dispatch`) and pick the
   increment type. It opens a `bump: release vX.Y.Z` pull request that updates `CHANGELOG.md`,
   `.cz.yaml` and `setup.py`.
2. Merge that pull request. **Release - tag & publish** detects the `bump: release` commit on
   `main` and creates the `vX.Y.Z` tag from the version in `.cz.yaml`.
3. The same workflow run then builds the sdist and wheel, publishes them to PyPI via trusted
   publishing (environment `pypi`, no API token) and creates the GitHub release with the changelog
   section for that version.

Nothing has to be built, tagged or uploaded from a developer machine.

## Increment types

`auto` lets commitizen determine the increment from the commit messages. Pass `PATCH`, `MINOR` or
`MAJOR` explicitly to override it.

`release-candidate` (from `main` or a `patch-release-*` branch) creates `X.Y.Z-rc.N`, and
`experimental` (only from an `experimental-*` branch) creates `X.Y.Z-alpha.N`. Both are published
as GitHub pre-releases.

## Workflows

| File | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/pr-checks.yaml` | pull request | Validate the conventional commit messages |
| `.github/workflows/release-changelog.yaml` | manual | Version bump, changelog, release PR |
| `.github/workflows/release-publish.yaml` | push to `main` | Tag the release commit, build, publish to PyPI, create the GitHub release |

The workflows call local composite actions in `.github/actions/`, which are vendored copies of
`apheris/github-actions@53a666f9` (v4.1.2):

| Local action | Upstream |
| --- | --- |
| `.github/actions/validate-conventional-commits` | `validate-conventional-commits` |
| `.github/actions/generate-changelog` | `generate-changelog/python-commitizen` |
| `.github/actions/tag` | `tag` |

They had to be copied because `apheris/github-actions` is private and cannot be resolved from this
public repository. Each file documents its provenance and the local deviations, the most relevant
being that the commitizen plugin is installed from the checkout (`pip install .`) instead of from
PyPI, so the repository validates and releases itself with the code under review. The upstream
behaviour of promoting an auto-detected `PATCH` on `main` to `MINOR` was dropped, since this
project releases patches directly from `main`.

When the upstream actions change in a relevant way, re-copy them and keep the header comments up to
date. Third-party actions inside them stay pinned by commit SHA so Renovate can propose updates.

## Required configuration

* PyPI trusted publisher for the project: repository `apheris/cz-github-jira-conventional`,
  workflow `release-publish.yaml`, environment `pypi`
  (see the [PyPI docs](https://docs.pypi.org/trusted-publishers/)).
* A GitHub environment named `pypi`. Add required reviewers there if the publish step should be
  manually approved.

No Actions secrets are needed: PyPI is reached through OIDC, and the bump PR, the tag and the
GitHub release are created with the built-in `GITHUB_TOKEN`.

## Why no releaser app

Other Apheris repositories pass the `releaser-apheris` app credentials
(`RELEASER_APHERIS_APP_ID` / `RELEASER_APHERIS_APP_PRIVATE_KEY`) to these shared actions. Those
organization secrets have `visibility: selected` and are granted through
`enable_releaser_app_secret` in `apheris/github-repositories`, where this repository is not
managed, so they are unavailable here.

This costs less than it sounds:

* The bump commit is **still signed and shows as Verified**. The changelog action commits
  through [`planetscale/ghcommit-action`](https://github.com/planetscale/ghcommit-action), which
  uses the GraphQL `createCommitOnBranch` API, and GitHub signs those commits with its own GPG key.
  The only difference is the author: `github-actions[bot]` instead of the releaser app.
* The annotated tag object is created through the REST API and is not GPG-signed. That is also true
  for the repositories that use the app, since the API does not sign tag objects.
* Tags created with `GITHUB_TOKEN` do not trigger workflows, so tagging, building, publishing and
  the GitHub release all run as chained jobs in the single `release-publish.yaml` run instead of
  being split across a tag-push trigger.

If the repository is added to the Terraform-managed set later, switch both workflows to
`actions/create-github-app-token` and the `tag` action can then trigger a separate publish workflow.

The Aikido `release-gate` shared action is intentionally not used: it needs the
`AIKIDO_CLIENT_API_KEY` secret, which is likewise not available here, and it is meant for
repositories where Renovate continuously uplifts dependencies. Aikido still checks this repository
through its GitHub App on every pull request.

## Note on bootstrapping

The local changelog and validation actions install the plugin from the checkout (`pip install .`),
so a release is prepared with the very code that is being released and pull requests are validated
against the rules they change. If a change breaks commit parsing or changelog rendering, it breaks
its own release workflow rather than shipping silently.

## Manual fallback

Only needed if the workflows are unavailable:

```bash
cz bump --changelog          # bumps .cz.yaml + setup.py, writes CHANGELOG.md, creates the tag
python -m build              # sdist + wheel into dist/
python -m twine upload dist/*
```

`twine` needs a PyPI API token (`__token__` as the username, `pypi-…` as the password) from
<https://pypi.org/manage/account/>.
