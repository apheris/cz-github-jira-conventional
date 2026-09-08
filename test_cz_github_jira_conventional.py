import re

import pytest
from commitizen import config

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
