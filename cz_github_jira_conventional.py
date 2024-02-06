import os
import re
from typing import Any, Dict, List

from commitizen import defaults, git, config
from commitizen.cz.base import BaseCommitizen
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
    bump_pattern = defaults.bump_pattern
    bump_map = defaults.bump_map
    commit_parser = defaults.commit_parser
    changelog_pattern = defaults.bump_pattern

    # Read the config file and check if required settings are available
    conf = config.read_cfg()
    jira_prefix_hint = ""
    if "jira_prefix" in conf.settings:
        jira_prefix = conf.settings["jira_prefix"]
        issue_multiple_hint = "42, 123"
        # if there is only one project prefix, show it as prefix hint
        if not isinstance(jira_prefix, list):
            jira_prefix_hint = jira_prefix
    else:
        jira_prefix = ""
        issue_multiple_hint = "XZ-42, XY-123"

    if "jira_base_url" not in conf.settings:
        print(
            "Please add the key jira_base_url to your .cz.yaml|json|toml config file."
        )
        quit()
    
    if "github_repo" not in conf.settings:
        print("Please add the key github_repo to your .cz.yaml|json|toml config file.")
        quit()
    
    jira_base_url = conf.settings["jira_base_url"]
    github_repo = conf.settings["github_repo"]
    
    if "github_base_url" not in conf.settings:
        github_base_url = DEFAULT_GITHUB_BASE_URL
    else:
        github_base_url = conf.settings["github_base_url"]
    
    if "change_type_map" not in conf.settings:
        change_type_map = DEFAULT_CHANGE_TYPE_MAP
    else:
        #change_type_map = conf.settings["change_type_map"]
        print("Only default change type map is supported at the moment.")
        quit()

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
        Require and validate the scope to be Jira ids.
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

    def schema_pattern(self) -> str:
        PATTERN = (
            r"(build|ci|docs|feat|fix|perf|refactor|style|test|chore|revert|bump)?!?"
            r"(\(\S+\)):(\s.*)"
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
            parsed_message["scope"] = " ".join(
                [
                    f"[{issue_id}]({self.jira_base_url}/browse/{issue_id})"
                    for issue_id in parsed_message["scope"].split(",")
                ]
            )
        parsed_message[
            "message"
        ] = f"{m} [{rev[:5]}]({self.github_base_url}/{self.github_repo}/commit/{commit.rev})"
        return parsed_message


class InvalidAnswerError(CzException):
    ...
