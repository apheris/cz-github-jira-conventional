# cz-github-jira-conventional

**cz-github-jira-conventional** is a plugin for the [**commitizen tools**](https://github.com/commitizen-tools/commitizen), a toolset that helps you to create [**conventional commit messages**](https://www.conventionalcommits.org/en/v1.0.0/). Since the structure of conventional commits messages is standardized they are machine readable and allow commitizen to automaticially calculate and tag [**semantic version numbers**](https://semver.org/) as well as create **CHANGELOG.md** files for your releases.

This plugin extends the commitizen tools by:
- **require a Jira issue id** in the commit message
- **create links to GitHub** commits in the CHANGELOG.md
- **create links to Jira** issues in the CHANGELOG.md

When you call commitizen `commit` you will be required you to enter the scope of your commit as a Jira issue id (or multiple issue ids, prefixed or without prefix, see config below).
```
> cz commit
? Select the type of change you are committing fix: A bug fix. Correlates with PATCH in SemVer
? JIRA issue number (multiple "42, 123"). XX-
...
```

The changelog created by cz (`cz bump --changelog`)will contain links to the commits in Github and the Jira issues.
```markdown
## v1.0.0 (2021-08-06)

### Features

- **[XX-123](https://myproject.atlassian.net/browse/XX-123)**: create changelogs with links to issues and commits [a374b](https://github.com/apheris/cz-github-jira-conventional/commit/a374b93f39327964f5ab5290252b795647906008)
- **[XX-42](https://myproject.atlassian.net/browse/XX-42),[XX-13](https://myproject.atlassian.net/browse/XX-13)**: allow multiple issue to be referenced in the commit [07ab0](https://github.com/apheris/cz-github-jira-conventional/commit/07ab0e09de36712ab1db93fff0c821ecd80b5849)
``` 


## Installation

Install with pip
`python -m pip install cz-github-jira-conventional` 

You need to use a cz config file that has the **required** additional values `jira_base_url` and `github_repo` and may contain the **optional** value `jira_prefix`.

Example `.cz.yaml` config for this repository
```yaml
commitizen:
  name: cz_github_jira_conventional
  tag_format: v$version
  version: 1.0.0
  jira_prefix: XX-
  jira_base_url: https://myproject.atlassian.net
  github_repo: apheris/cz-github-jira-conventional
```

The `jira_prefix` can be either 
- empty (the user must write the prefix for each issue)
- a string (the prefix will be added automatically)
- a list (for multiple projects, the user will be asked to choose a prefix)

```yaml
  jira_prefix: 
    - XX-
    - XY-
    - YY-
```

### pre-commit
Add this plugin to the dependencies of your commit message linting with `pre-commit`. 

Example `.pre-commit-config.yaml` file.
```yaml
repos:
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v2.17.13
    hooks:
      - id: commitizen
        stages: [commit-msg]
        additional_dependencies: [cz-github-jira-conventional]
```
Install the hook with 
```bash
pre-commit install --hook-type commit-msg
```

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
This plugin would not have been possible without the fantastic work from:
* [commitizen tools](https://github.com/commitizen-tools/commitizen)
* [conventional_JIRA](https://github.com/Crystalix007/conventional_jira)
