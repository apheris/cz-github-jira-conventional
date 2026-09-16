"""Exercise the workflows' actual shell steps without calling GitHub or PyPI."""

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).parent
PUBLISH = ROOT / ".github/workflows/release-publish.yaml"
TAG = ROOT / ".github/actions/tag/action.yaml"
CHANGELOG = ROOT / ".github/actions/generate-changelog/action.yaml"


def steps(path, job=None):
    workflow = yaml.safe_load(path.read_text())
    return workflow["jobs"][job]["steps"] if job else workflow["runs"]["steps"]


def run_step(step, tmp_path, **env):
    output = tmp_path / "github-output"
    output.write_text("")
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_ENV": str(output),
            **env,
        },
        capture_output=True,
        text=True,
    )
    return result, dict(line.split("=", 1) for line in output.read_text().splitlines())


@pytest.mark.parametrize("path,job", [(PUBLISH, "prepare"), (TAG, None)])
@pytest.mark.parametrize(
    "message,version",
    [
        ("bump: release v1.2.3", "1.2.3"),
        ("bump: release v0.0.0", "0.0.0"),
        ("bump: release v1.2.3-rc.0", "1.2.3-rc.0"),
        ("bump: release v1.2.3-rc.12 (#123)", "1.2.3-rc.12"),
        ("bump: release v1.2.3 (#123)\n\nRelease notes", "1.2.3"),
        ("bump: release-notes", None),
        ("bump: release", None),
        ("bump: release 1.2.3", None),
        ("bump: release v1.2", None),
        ("bump: release v01.2.3", None),
        ("bump: release v1.2.3-rc.01", None),
        ("bump: release v1.2.3-alpha.0", None),
        ("bump: release v1.2.3 extra", None),
        ("bump: release v1.2.3+build", None),
        ("fix: docs\n\nbump: release v1.2.3", None),
        ("bump:\trelease v1.2.3", None),
        ("", None),
    ],
)
def test_release_commit_detection(tmp_path, path, job, message, version):
    step = next(s for s in steps(path, job) if s.get("id") == "release-check")
    result, outputs = run_step(step, tmp_path, COMMIT_MESSAGE=message)
    assert result.returncode == 0, result.stderr
    assert outputs == ({"do-release": "true", "version": version} if version else {})


@pytest.mark.parametrize("path,job", [(PUBLISH, "prepare"), (TAG, None)])
@pytest.mark.parametrize(
    "config_version,setup_version,release_version,valid",
    [
        ("1.2.3", "1.2.3", "1.2.3", True),
        ("1.2.3-rc.0", "1.2.3-rc.0", "1.2.3-rc.0", True),
        ("1.2.3", "1.2.3", "1.2.4", False),
        ("null", "1.2.3", "1.2.3", False),
        ("1.2.3", "1.2.4", "1.2.3", False),
    ],
)
def test_version_must_match_release_commit(
    tmp_path, path, job, config_version, setup_version, release_version, valid
):
    if path == TAG and config_version != setup_version:
        # setup.py is cross-checked by prepare, before the tag action runs.
        valid = config_version == release_version
    step = next(
        s for s in steps(path, job) if s.get("id") in ("version", "get-release-version")
    )
    # Replace only the external yq command; execute the actual comparison logic.
    yq = tmp_path / "yq"
    yq.write_text('#!/bin/sh\nprintf "%s\\n" "$CONFIG_VERSION"\n')
    yq.chmod(0o755)
    (tmp_path / "setup.py").write_text(f'version="{setup_version}"\n')
    result, outputs = run_step(
        step,
        tmp_path,
        PATH=f"{tmp_path}:{os.environ['PATH']}",
        CONFIG_VERSION=config_version,
        FILE_PATH=".cz.yaml",
        RELEASE_VERSION=release_version,
    )
    assert (result.returncode == 0) == valid, result.stdout + result.stderr
    assert outputs == ({"tag": f"v{release_version}"} if valid else {})


@pytest.mark.parametrize(
    "increment", ["auto", "PATCH", "MINOR", "MAJOR", "release-candidate"]
)
@pytest.mark.parametrize(
    "branch,valid",
    [
        ("main", True),
        ("patch-release-3", True),
        ("feature/test", False),
        ("patch-release-3/nested", False),
        ("experimental-test", False),
    ],
)
def test_release_base_validation(tmp_path, increment, branch, valid):
    result, _ = run_step(
        steps(CHANGELOG)[0], tmp_path, BASE_BRANCH=branch, INCREMENT_TYPE=increment
    )
    assert (result.returncode == 0) == valid


@pytest.mark.parametrize("increment", ["experimental", "alpha", "", "patch"])
def test_unsupported_increment_is_rejected(tmp_path, increment):
    result, _ = run_step(
        steps(CHANGELOG)[0], tmp_path, BASE_BRANCH="main", INCREMENT_TYPE=increment
    )
    assert result.returncode != 0


def test_publication_requires_protected_refs():
    jobs = yaml.safe_load(PUBLISH.read_text())["jobs"]
    assert jobs["prepare"]["if"] == "github.ref_protected"
    assert jobs["publish-pypi"]["if"] == "github.ref_protected"
    assert jobs["publish-pypi"]["environment"]["name"] == "pypi"


def test_changelog_requires_protected_release_workflow_ref():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/release-changelog.yaml").read_text()
    )
    job = workflow["jobs"]["create-changelog"]
    assert job["if"] == (
        "github.ref_protected && "
        "(github.ref == 'refs/heads/main' || "
        "startsWith(github.ref, 'refs/heads/patch-release-'))"
    )


@pytest.mark.parametrize(
    "old_version,prerelease,expected",
    [
        ("1.2.3", False, "1.2.4"),
        ("1.2.3", True, "1.2.4-rc.0"),
        ("1.2.4-rc.0", False, "1.2.4"),
        ("1.2.4-rc.0", True, "1.2.4-rc.1"),
    ],
)
def test_bump_updates_both_version_files_and_generates_release_header(
    tmp_path, old_version, prerelease, expected
):
    for name in (".cz.yaml", "setup.py", "README.md"):
        shutil.copy(ROOT / name, tmp_path / name)
    # Exercise real configuration, but never derive fixtures from the current release version.
    config_path = tmp_path / ".cz.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["commitizen"]["version"] = old_version
    config_path.write_text(yaml.safe_dump(config))
    setup_path = tmp_path / "setup.py"
    setup, replacements = re.subn(
        r'(?m)^(\s*version=)"[^"]+"',
        rf'\g<1>"{old_version}"',
        setup_path.read_text(),
    )
    assert replacements == 1
    setup_path.write_text(setup)

    def run(*args):
        return subprocess.run(
            args, cwd=tmp_path, check=True, capture_output=True, text=True
        )

    run("git", "init", "-b", "main")
    run("git", "config", "user.name", "Release test")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "commit.gpgsign", "false")
    run("git", "config", "tag.gpgsign", "false")
    run("git", "config", "core.hooksPath", "/dev/null")
    run("git", "add", ".")
    run("git", "commit", "-m", "feat: initial version")
    run("git", "tag", f"v{old_version}")
    run("git", "commit", "--allow-empty", "-m", "fix: release regression")
    args = [
        "cz",
        "bump",
        "--files-only",
        "--changelog",
        "--yes",
        "--increment",
        "PATCH",
    ]
    if prerelease:
        args.extend(["--prerelease", "rc"])
    run(*args)

    config = yaml.safe_load((tmp_path / ".cz.yaml").read_text())
    assert config["commitizen"]["version"] == expected
    assert f'version="{expected}"' in (tmp_path / "setup.py").read_text()
    assert f"## v{expected} " in (tmp_path / "CHANGELOG.md").read_text()
    step = next(s for s in steps(CHANGELOG) if s.get("name") == "Next version tag")
    result, outputs = run_step(step, tmp_path)
    assert result.returncode == 0, result.stderr
    assert outputs["NEXT_VERSION_TAG"] == f"v{expected}"
    detection = next(
        s for s in steps(PUBLISH, "prepare") if s.get("id") == "release-check"
    )
    result, outputs = run_step(
        detection,
        tmp_path,
        COMMIT_MESSAGE=f"bump: release {outputs['NEXT_VERSION_TAG']}",
    )
    assert result.returncode == 0, result.stderr
    assert outputs == {"do-release": "true", "version": expected}
