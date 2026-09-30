## v4.0.0 (2026-09-30)

### BREAKING CHANGE

- commits with a scope that is not a comma-separated list of Jira issue IDs no longer pass `cz check`. [8dca1](https://github.com//apheris/cz_github_jira_conventional/commit/8dca1e6d9155fe73e010064eef7b04f9b729e3b1)

### Feat

- enforce Jira issue IDs in the schema pattern [8dca1](https://github.com//apheris/cz_github_jira_conventional/commit/8dca1e6d9155fe73e010064eef7b04f9b729e3b1)

### Fix

- restrict jira scope separators to horizontal whitespace [be3ea](https://github.com//apheris/cz_github_jira_conventional/commit/be3ea312a1b37288f534c4deb75866ac90497ed4)
- handle optional Jira scope in commit wizard [d299d](https://github.com//apheris/cz_github_jira_conventional/commit/d299dc7d47009e696d9d07e270bae123ab1ee6b6)
- trim Jira scope entries before rendering changelog links [40db5](https://github.com//apheris/cz_github_jira_conventional/commit/40db540ef75350c09fdd80237176d8c52bbcf82f)
- update wheel from 0.46.2 to 0.48.0 [d2f3d](https://github.com//apheris/cz_github_jira_conventional/commit/d2f3da4fd70e5eb77182bbc09beae39b698eb422)
- update setuptools from 78.1.1 to 83.0.0 [ca544](https://github.com//apheris/cz_github_jira_conventional/commit/ca544c9e2b4a526d5691b9e762ab604e9acfa489)

## v3.0.2 (2025-06-04)

### Fix

- broken import cz default [e9520](https://github.com//apheris/cz_github_jira_conventional/commit/e9520b967584c101f1281b424d87395d0feb2695)

## v3.0.1 (2024-06-12)

### Fix

- fix the install_requires commitizen version [951b5](https://github.com//apheris/cz_github_jira_conventional/commit/951b508a3d12833cb69364ca92e16b5b9d724926)

## v3.0.0 (2024-06-12)

### Fix

- **[XX-9](https://myproject.atlassian.net/browse/XX-9)**: import of default commit parser [8923d](https://github.com//apheris/cz_github_jira_conventional/commit/8923d361adc983b0ad6260631530d0fb60aaef74)

## v2.0.0 (2023-06-15)

### Feat

- **[XX-0425](https://myproject.atlassian.net/browse/XX-0425)**: migrate to new plugin format [aaa35](https://github.com//apheris/cz_github_jira_conventional/commit/aaa35fbfbd95ee313916ac175f11efbf55635fab)
- support custom github base URL [d1a32](https://github.com//apheris/cz_github_jira_conventional/commit/d1a322beabf402594d2a00abd9270e4c1c09d035)

## v1.1.0 (2022-07-26)

### Feat

- **[XX-2815](https://myproject.atlassian.net/browse/XX-2815)**: allow choosing between multiple Jira projects [469b9](https://github.com/apheris/cz_github_jira_conventional/commit/469b94c3bb3aa61c6b8c53627c064e5921b4d912)

## v1.0.0 (2021-08-13)

### Feat

- **[XX-443](https://myproject.atlassian.net/browse/XX-443)**: create cz customization script that links github and jira [271e7](https://github.com/apheris/cz_github_jira_conventional/commit/271e78a3d8505192615702434ef9839b2ef3c08c)
