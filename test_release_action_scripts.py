"""Execute the composite actions' JavaScript with mocked GitHub API responses."""

import json
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).parent
CHANGELOG = ROOT / ".github/actions/generate-changelog/action.yaml"
TAG = ROOT / ".github/actions/tag/action.yaml"


def action_steps(path):
    return yaml.safe_load(path.read_text())["runs"]["steps"]


def run_script(step, setup):
    script = json.dumps(step["with"]["script"])
    result = subprocess.run(
        [
            "node",
            "-e",
            f"""
            const assert = require('node:assert/strict');
            const context = {{ repo: {{ owner: 'apheris', repo: 'example' }}, sha: 'release-sha' }};
            const outputs = {{}};
            const core = {{ setOutput: (key, value) => outputs[key] = value, info: () => {{}} }};
            const AsyncFunction = Object.getPrototypeOf(async function() {{}}).constructor;
            const script = new AsyncFunction('github', 'context', 'core', {script});
            const apiError = status => Object.assign(new Error(`API ${{status}}`), {{ status }});
            (async () => {{
              {setup}
            }})().catch(error => {{ console.error(error); process.exitCode = 1; }});
            """,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("protection", [True, False, None])
def test_release_base_protection(protection):
    step = next(s for s in action_steps(CHANGELOG) if s.get("id") == "release-base")
    run_script(
        step,
        f"""
        process.env.BASE_BRANCH = 'patch-release-3';
        const github = {{ rest: {{ repos: {{ getBranch: async args => {{
          assert.deepEqual(args, {{ ...context.repo, branch: 'patch-release-3' }});
          return {{ data: {{ protected: {json.dumps(protection)}, commit: {{ sha: 'verified-sha' }} }} }};
        }} }} }} }};
        if ({json.dumps(protection)} === true) {{
          await script(github, context, core);
          assert.deepEqual(outputs, {{ sha: 'verified-sha' }});
        }} else {{
          await assert.rejects(script(github, context, core), /not protected/);
          assert.deepEqual(outputs, {{}});
        }}
        """,
    )


@pytest.mark.parametrize("status", [403, 404, 500])
def test_release_base_lookup_fails_closed(status):
    step = next(s for s in action_steps(CHANGELOG) if s.get("id") == "release-base")
    run_script(
        step,
        f"""
        const github = {{ rest: {{ repos: {{ getBranch: async () => {{ throw apiError({status}); }} }} }} }};
        await assert.rejects(script(github, context, core), {{ status: {status} }});
        assert.deepEqual(outputs, {{}});
        """,
    )


def test_changelog_checks_protection_before_checkout_and_pins_verified_commit():
    steps = action_steps(CHANGELOG)
    validation = next(i for i, s in enumerate(steps) if s.get("id") == "release-base")
    checkout = next(
        i
        for i, s in enumerate(steps)
        if s.get("uses", "").startswith("actions/checkout@")
    )
    install = next(
        i for i, s in enumerate(steps) if s.get("name") == "Install dependencies"
    )
    assert validation < checkout < install
    assert steps[checkout]["with"]["ref"] == "${{ steps.release-base.outputs.sha }}"
    assert steps[checkout]["with"]["persist-credentials"] is False
    base = next(s for s in steps if s.get("name") == "Use verified release base commit")
    assert base["env"]["BASE_SHA"] == "${{ steps.release-base.outputs.sha }}"
    assert "BASE_BRANCH_SHA=$BASE_SHA" in base["run"]


@pytest.mark.parametrize(
    "scenario",
    [
        "new",
        "lightweight",
        "annotated",
        "nested",
        "wrong-commit",
        "wrong-type",
        "lookup-error",
        "tag-lookup-error",
        "create-tag-error",
        "create-ref-error",
        "race-match",
        "race-mismatch",
        "race-missing",
    ],
)
def test_tag_creation_and_retry(scenario):
    step = next(s for s in action_steps(TAG) if s.get("name") == "Create tag")
    run_script(
        step,
        f"""
        process.env.RELEASE_TAG = 'v1.2.3';
        const scenario = {json.dumps(scenario)};
        const calls = [];
        let lookups = 0;
        const creates = ['new', 'create-tag-error', 'create-ref-error', 'race-match', 'race-mismatch', 'race-missing'].includes(scenario);
        const github = {{ rest: {{ git: {{
          getRef: async args => {{
            assert.deepEqual(args, {{ ...context.repo, ref: 'tags/v1.2.3' }});
            calls.push('getRef');
            lookups++;
            if (scenario === 'lookup-error') throw apiError(403);
            if (creates && lookups === 1 || scenario === 'race-missing') throw apiError(404);
            const annotated = ['annotated', 'nested', 'tag-lookup-error'].includes(scenario);
            return {{ data: {{ object: {{
              type: annotated ? 'tag' : scenario === 'wrong-type' ? 'tree' : 'commit',
              sha: annotated ? 'tag-sha' : ['wrong-commit', 'race-mismatch'].includes(scenario) ? 'other-sha' : context.sha,
            }} }} }};
          }},
          getTag: async args => {{
            calls.push('getTag');
            assert.deepEqual(args, {{ ...context.repo, tag_sha: args.tag_sha }});
            if (scenario === 'tag-lookup-error') throw apiError(500);
            if (scenario === 'nested' && args.tag_sha === 'tag-sha') {{
              return {{ data: {{ object: {{ type: 'tag', sha: 'inner-tag' }} }} }};
            }}
            return {{ data: {{ object: {{ type: 'commit', sha: context.sha }} }} }};
          }},
          createTag: async args => {{
            calls.push('createTag');
            assert.deepEqual(args, {{ ...context.repo, tag: 'v1.2.3', message: 'Release v1.2.3', object: context.sha, type: 'commit' }});
            if (scenario === 'create-tag-error') throw apiError(500);
            return {{ data: {{ sha: 'new-tag-sha' }} }};
          }},
          createRef: async args => {{
            calls.push('createRef');
            assert.deepEqual(args, {{ ...context.repo, ref: 'refs/tags/v1.2.3', sha: 'new-tag-sha' }});
            if (scenario === 'create-ref-error') throw apiError(403);
            if (scenario.startsWith('race-')) throw apiError(422);
            return {{ data: {{}} }};
          }},
        }} }} }};
        if (['wrong-commit', 'wrong-type', 'race-mismatch'].includes(scenario)) {{
          await assert.rejects(script(github, context, core), /does not resolve to release commit/);
        }} else if (scenario.endsWith('-error') || scenario === 'race-missing') {{
          await assert.rejects(script(github, context, core), /API/);
        }} else {{
          await script(github, context, core);
        }}
        assert.equal(calls.filter(c => c === 'createTag').length, creates ? 1 : 0);
        assert.equal(calls.filter(c => c === 'createRef').length, creates && scenario !== 'create-tag-error' ? 1 : 0);
        if (scenario.startsWith('race-')) assert.equal(lookups, 2);
        if (scenario === 'nested') assert.equal(calls.filter(c => c === 'getTag').length, 2);
        """,
    )


def test_all_python_setup_steps_use_shared_version_file():
    paths = list((ROOT / ".github/workflows").glob("*.yaml")) + list(
        (ROOT / ".github/actions").glob("*/action.yaml")
    )
    found = 0
    for path in paths:
        config = yaml.safe_load(path.read_text())
        groups = config.get("jobs", {"action": config.get("runs", {})}).values()
        for group in groups:
            for step in group.get("steps", []):
                if step.get("uses", "").startswith("actions/setup-python@"):
                    assert (
                        step["with"]["python-version-file"] == ".python-version"
                    ), path
                    assert "python-version" not in step["with"], path
                    found += 1
    assert found > 0
