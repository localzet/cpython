# Publish a standalone GitHub repository and PyPI prerelease

The source in experimental/schema-compat-standalone is publicly accessible,
but **the GitHub connector cannot create new repositories** and has no PyPI
publishing credentials. As a result, publishing a release requires actions
in the repository owner's accounts. Do not publish from the CPython fork.

## 1. Create an independent public GitHub repository

Use the source ZIP produced by the successful CI build (not the fork's git
history). Extract its contents into an empty local directory.

    cd /path/to/extracted/schema-compat
    git init -b main
    git add .
    git commit -m "Initial prerelease 0.1.0a1"
    gh auth login
    gh repo create localzet/schema-compat --public --source=. --remote=origin --push

Do not run gh repo create if the repository already exists. For an existing
empty repository, add it as origin and push main normally.

## 2. Configure PyPI's Trusted Publisher

On PyPI, create a pending trusted publisher for the project
"localzet-schema-compat" or configure it on an existing owned project. The
project name must not be taken by another owner.

- GitHub owner: localzet
- GitHub repository: schema-compat
- Workflow filename: release.yml
- GitHub environment: pypi

Create the GitHub environment named "pypi" and, when available, protect it
with manual approvals and allowed tag refs. No long-lived PyPI token is
needed; the official PyPA GitHub Action uses OIDC with a short-lived token.

Before publishing, verify the repository license, metadata, version, README
and build artifacts. Run the CI on the new default branch.

## 3. Publish v0.1.0a1

From the *new independent repository* (not the original CPython fork),
create a GitHub Release for tag v0.1.0a1 pointing at the tested commit.
This triggers .github/workflows/release.yml, which builds distributions,
runs runtime tests, checks metadata, and requests PyPI Trusted Publishing.
The workflow checks that the tag equals the version in pyproject.toml.

Confirm the GitHub release workflow succeeds and then verify the PyPI page.
**Until that happens, the project is not published to PyPI.**

## Safety

Never upload PyPI credentials or PATs into files or chat. Never grant OIDC
permissions to PR workflows. Only use Trusted Publishing after confirming
the GitHub owner/repository/workflow/environment identity. The release
workflow requests id-token: write only in the gated publication job.

Documentation: https://docs.pypi.org/trusted-publishers/using-a-publisher/
