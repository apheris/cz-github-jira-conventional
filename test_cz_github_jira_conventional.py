import re

import pytest
from commitizen import config, git

from cz_github_jira_conventional import GithubJiraConventionalCz


@pytest.fixture
def cz():
    """The plugin reads the `.cz.yaml` of this repository, which uses `XX-`."""
    return GithubJiraConventionalCz(config.read_cfg())


def check(cz, message):
    return re.match(cz.schema_pattern(), message) is not None


@pytest.mark.parametrize(
    "message",
    [
        "fix: correct minor typos in code",
        "fix(XX-42): correct minor typos in code",
        "feat(XX-42,XX-123): allow multiple issues",
        "feat(XX-42, XX-123): allow a space after the comma",
        "feat(XX-42)!: mark a breaking change",
        "bump: version 1.0.0 → 1.0.1",
    ],
)
def test_valid_messages(cz, message):
    assert check(cz, message)


@pytest.mark.parametrize(
    "message",
    [
        "fix(foundry): a free form scope is not a jira issue",
        "fix(ui): a free form scope is not a jira issue",
        "fix(XX-): a prefix without a number is not a jira issue",
        "fix(42): a number without a prefix is not a jira issue",
        "fix(YY-42): an unconfigured prefix is not accepted",
        "fix(XX-42,ui): every scope entry has to be a jira issue",
        "unknown(XX-42): the type has to be a conventional commit type",
    ],
)
def test_invalid_messages(cz, message):
    assert not check(cz, message)


@pytest.mark.parametrize(
    "whitespace", ["\n", "\r", "\r\n", "\v", "\f", "\u0085", "\u2028", "\u2029"]
)
def test_scope_rejects_line_breaks_after_comma(cz, whitespace):
    assert not check(cz, f"fix(XX-42,{whitespace}XX-123): reject multiline scopes")


@pytest.mark.parametrize("separator", [",", ", ", ",\t"])
def test_changelog_trims_jira_issue_ids(cz, separator):
    scope = separator.join(["XX-42", "XX-123", "XX-456"])
    message = f"feat({scope}): allow multiple issues"
    assert check(cz, message)
    parsed_message = re.match(cz.commit_parser, message).groupdict()
    commit = git.GitCommit(rev="abcdef123456", title=message)

    result = cz.changelog_message_builder_hook(parsed_message, commit)

    assert result["scope"] == (
        f"[XX-42]({cz.jira_base_url}/browse/XX-42) "
        f"[XX-123]({cz.jira_base_url}/browse/XX-123) "
        f"[XX-456]({cz.jira_base_url}/browse/XX-456)"
    )
    assert result["message"] == (
        f"allow multiple issues [abcde]"
        f"({cz.github_base_url}/{cz.github_repo}/commit/abcdef123456)"
    )


@pytest.mark.parametrize(
    "jira_prefix, selected_prefix, scope_input, expected_scope",
    [
        ("XX-", None, "", ""),
        ("", None, "", ""),
        (["XX-", "XY-"], "XY-", "", ""),
        ("XX-", None, "42, 123", "(XX-42,XX-123)"),
        ("", None, "XX-42, XY-123", "(XX-42,XY-123)"),
        (["XX-", "XY-"], "XY-", "42, 123", "(XY-42,XY-123)"),
    ],
)
def test_wizard_renders_optional_jira_scope(
    cz, monkeypatch, jira_prefix, selected_prefix, scope_input, expected_scope
):
    monkeypatch.setattr(cz, "jira_prefix", jira_prefix)
    scope_question = next(q for q in cz.questions() if q["name"] == "scope")
    answers = {
        "prefix": "fix",
        "scope": scope_question["filter"](scope_input),
        "subject": "correct minor typos in code",
        "body": "",
        "footer": "",
        "is_breaking_change": False,
    }
    if selected_prefix is not None:
        answers["issue_jira_prefix"] = selected_prefix

    message = cz.message(answers)

    assert message == f"fix{expected_scope}: correct minor typos in code"
    assert check(cz, message)


def test_process_commit_still_returns_the_message(cz):
    assert (
        cz.process_commit("fix(XX-42): correct minor typos in code")
        == "correct minor typos in code"
    )


def test_multiple_prefixes_are_accepted(cz, monkeypatch):
    monkeypatch.setattr(GithubJiraConventionalCz, "jira_prefix", ["XX-", "XY-"])

    assert check(cz, "fix(XY-42): a configured prefix is accepted")
    assert check(cz, "fix(XX-42,XY-43): prefixes may be mixed")
    assert not check(cz, "fix(YY-42): an unconfigured prefix is not accepted")


def test_without_a_configured_prefix_any_prefix_is_accepted(cz, monkeypatch):
    monkeypatch.setattr(GithubJiraConventionalCz, "jira_prefix", "")

    assert check(cz, "fix(YY-42): the user writes the prefix themselves")
    assert not check(cz, "fix(42): a number without a prefix is not a jira issue")
