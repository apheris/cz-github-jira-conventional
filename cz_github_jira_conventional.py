import os
import re
from typing import Any, Dict, List

from commitizen import defaults, git
from commitizen.config.base_config import BaseConfig
from commitizen.exceptions import InvalidConfigurationError
from commitizen.cz.base import BaseCommitizen
from commitizen.cz.conventional_commits import ConventionalCommitsCz
from commitizen.cz.utils import multiple_line_breaker, required_validator
from commitizen.cz.exceptions import CzException

__all__ = ["GithubJiraConventionalCz"]

DEFAULT_GITHUB_BASE_URL = "https://github.com/"
DEFAULT_CHANGE_TYPE_MAP = {
    "feat": "Feat",
    "fix": "Fix",
    "refactor": "Refactor",
    "perf": "Perf",
}


def parse_subject(text):
    if isinstance(text, str):
        text = text.strip(".").strip()

    return required_validator(text, msg="Subject is required.")


class GithubJiraConventionalCz(BaseCommitizen):
    bump_pattern = defaults.BUMP_PATTERN
    bump_map = defaults.BUMP_MAP
    commit_parser = ConventionalCommitsCz.commit_parser
    changelog_pattern = defaults.BUMP_PATTERN

    def __init__(self, config: BaseConfig) -> None:
        # Commitizen imports every installed plugin during discovery, even when a
        # different plugin is selected. Read and validate the project config only
        # when this plugin is actually instantiated.
        super().__init__(config)
        settings = self.config.settings
        self.jira_prefix = settings.get("jira_prefix", "")
        self.issue_multiple_hint = (
            "42, 123" if self.jira_prefix else "XZ-42, XY-123"
        )
        self.jira_prefix_hint = (
            self.jira_prefix if isinstance(self.jira_prefix, str) else ""
        )

        for key in ("jira_base_url", "github_repo"):
            if not settings.get(key):
                raise InvalidConfigurationError(
                    f"Please add the key {key} to your .cz.yaml|json|toml config file."
                )
        self.jira_base_url = settings["jira_base_url"]
        self.github_repo = settings["github_repo"]
        self.github_base_url = settings.get("github_base_url", DEFAULT_GITHUB_BASE_URL)

        if "change_type_map" in settings:
            raise InvalidConfigurationError(
                "Only default change type map is supported at the moment."
            )
        self.change_type_map = DEFAULT_CHANGE_TYPE_MAP

    def questions(self) -> List[Dict[str, Any]]:
        questions: List[Dict[str, Any]] = [
            {
                "type": "list",
                "name": "prefix",
                "message": "Select the type of change you are committing",
                "choices": [
                    {
                        "value": "fix",
                        "name": "fix: A bug fix. Correlates with PATCH in SemVer",
                    },
                    {
                        "value": "feat",
                        "name": "feat: A new feature. Correlates with MINOR in SemVer",
                    },
                    {"value": "docs", "name": "docs: Documentation only changes"},
                    {
                        "value": "style",
                        "name": (
                            "style: Changes that do not affect the "
                            "meaning of the code (white-space, formatting,"
                            " missing semi-colons, etc)"
                        ),
                    },
                    {
                        "value": "refactor",
                        "name": (
                            "refactor: A code change that neither fixes "
                            "a bug nor adds a feature"
                        ),
                    },
                    {
                        "value": "perf",
                        "name": "perf: A code change that improves performance",
                    },
                    {
                        "value": "test",
                        "name": (
                            "test: Adding missing or correcting " "existing tests"
                        ),
                    },
                    {
                        "value": "build",
                        "name": (
                            "build: Changes that affect the build system or "
                            "external dependencies (example scopes: pip, docker, npm)"
                        ),
                    },
                    {
                        "value": "ci",
                        "name": (
                            "ci: Changes to our CI configuration files and "
                            "scripts (example scopes: GitLabCI)"
                        ),
                    },
                ],
            },
            {
                "type": "input",
                "name": "scope",
                "message": (
                    f'JIRA issue number (multiple "{self.issue_multiple_hint}"). {self.jira_prefix_hint}'
                ),
                "filter": self.parse_scope,
            },
            {
                "type": "input",
                "name": "subject",
                "filter": parse_subject,
                "message": (
                    "Write a short and imperative summary of the code changes: (lower case and no period)\n"
                ),
            },
            {
                "type": "input",
                "name": "body",
                "message": (
                    "Provide additional contextual information about the code changes: (press [enter] to skip)\n"
                ),
                "filter": multiple_line_breaker,
            },
            {
                "type": "confirm",
                "message": "Is this a BREAKING CHANGE? Correlates with MAJOR in SemVer",
                "name": "is_breaking_change",
                "default": False,
            },
            {
                "type": "input",
                "name": "footer",
                "message": (
                    "Footer. Information about Breaking Changes and "
                    "reference issues that this commit closes: (press [enter] to skip)\n"
                ),
            },
        ]
        # If there are multiple Jira prefixes let the user select one
        if isinstance(self.jira_prefix, list):
            questions.insert(
                1,
                {
                    "type": "list",
                    "name": "issue_jira_prefix",
                    "message": "JIRA project",
                    "choices": [
                        {"value": prefix, "name": prefix} for prefix in self.jira_prefix
                    ],
                },
            )
        return questions

    def parse_scope(self, text):
        """
        Validate a supplied scope as Jira IDs; allow an empty scope.
        """
        if self.jira_prefix:
            issueRE = re.compile(r"\d+")
        else:
            issueRE = re.compile(r"\w+-\d+")

        if not text:
            return ""

        issues = [i.strip() for i in text.strip().split(",")]
        for issue in issues:
            if not issueRE.fullmatch(issue):
                raise InvalidAnswerError(f"JIRA issue '{issue}' is not valid.")

        return required_validator(issues, msg="JIRA scope is required")

    def message(self, answers: dict) -> str:
        prefix = answers["prefix"]
        issue_jira_prefix = (
            answers["issue_jira_prefix"]
            if "issue_jira_prefix" in answers
            else self.jira_prefix
        )
        issues = answers["scope"]
        subject = answers["subject"]
        body = answers["body"]
        footer = answers["footer"]
        is_breaking_change = answers["is_breaking_change"]

        scope = ""
        if issues:
            # Add Jira prefixes to the issue numbers.
            issues_str = ",".join([issue_jira_prefix + i for i in issues])
            scope = f"({issues_str})"
        if body:
            body = f"\n\n{body}"
        if is_breaking_change:
            footer = f"BREAKING CHANGE: {footer}"
        if footer:
            footer = f"\n\n{footer}"

        message = f"{prefix}{scope}: {subject}{body}{footer}"

        return message

    def example(self) -> str:
        return (
            "fix: correct minor typos in code\n"
            "\n"
            "see the issue for details on the typos fixed\n"
            "\n"
            "closes issue #12"
        )

    def schema(self) -> str:
        return (
            "<type>(<scope>): <subject>\n"
            "<BLANK LINE>\n"
            "<body>\n"
            "<BLANK LINE>\n"
            "(BREAKING CHANGE: )<footer>"
        )

    def issue_pattern(self) -> str:
        """
        Pattern that a single Jira issue ID in the scope has to match.

        Mirrors the validation of `parse_scope`, which is only applied to the
        answers of the interactive `cz commit` prompt: if a prefix is configured,
        `message()` prepends it when building the commit message, so the ID must be
        prefix + number; otherwise the user has to write the prefix themselves.
        """
        if self.jira_prefix:
            prefixes = (
                self.jira_prefix
                if isinstance(self.jira_prefix, list)
                else [self.jira_prefix]
            )
            alternatives = "|".join(re.escape(prefix) for prefix in prefixes)
            return rf"(?:{alternatives})\d+"
        return r"\w+-\d+"

    def schema_pattern(self) -> str:
        issue = self.issue_pattern()
        # The scope is optional, but if it is present it must be a
        # comma-separated list of Jira issue IDs, because the changelog renders every
        # scope as a link to `<jira_base_url>/browse/<scope>`. Keep the number
        # of capturing groups at three, `process_commit` reads group 3.
        PATTERN = (
            r"(build|ci|docs|feat|fix|perf|refactor|style|test|chore|revert|bump)"
            rf"(\({issue}(?:,[ \t]?{issue})*\))?!?:(\s.*)"
        )
        return PATTERN

    def info(self) -> str:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        filepath = os.path.join(dir_path, "conventional_commits_info.txt")
        with open(filepath, "r") as f:
            content = f.read()
        return content

    def process_commit(self, commit: str) -> str:
        pat = re.compile(self.schema_pattern())
        m = re.match(pat, commit)
        if m is None:
            return ""
        return m.group(3).strip()

    def changelog_message_builder_hook(
        self, parsed_message: dict, commit: git.GitCommit
    ) -> dict:
        """add github and jira links to the readme"""
        rev = commit.rev
        m = parsed_message["message"]
        if parsed_message["scope"]:
            issue_ids = [issue.strip() for issue in parsed_message["scope"].split(",")]
            parsed_message["scope"] = " ".join(
                f"[{issue_id}]({self.jira_base_url}/browse/{issue_id})"
                for issue_id in issue_ids
            )
        parsed_message["message"] = (
            f"{m} [{rev[:5]}]({self.github_base_url}/{self.github_repo}/commit/{commit.rev})"
        )
        return parsed_message


class InvalidAnswerError(CzException): ...
