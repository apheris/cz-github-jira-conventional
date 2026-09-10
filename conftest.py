# Import commitizen before the plugin module to avoid a circular import:
# commitizen discovers plugins while it is imported, and this repository
# registers `cz_github_jira_conventional` as one, so importing the plugin
# module first would let commitizen re-enter the partially initialized module.
import commitizen  # noqa: F401
