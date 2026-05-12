# GitHub Actions reusable workflow

Add dqt to any GitHub repository's CI in 5 lines:

```yaml
# .github/workflows/data-quality.yml
jobs:
  dqt:
    uses: antonbarr-data/dqt/.github/workflows/dqt-check.yml@main
    with:
      checks_file: checks.yaml
    secrets:
      DQT_CONNECTION: ${{ secrets.WAREHOUSE_CONNECTION_STRING }}
```

The workflow installs `dqtlib` from PyPI, runs `dqt run checks.yaml --output junit`,
and posts JUnit results as a GitHub PR check.

## Inputs

| Input | Default | Description |
|---|---|---|
| `checks_file` | `checks.yaml` | Path to checks.yaml |
| `connection` | (empty) | Connection string -- prefer the secret |
| `python_version` | `3.12` | Python version |
| `fail_on_warn` | `false` | Fail on warn verdict |

## Secrets

| Secret | Description |
|---|---|
| `DQT_CONNECTION` | Warehouse connection string -- overrides `inputs.connection` |
