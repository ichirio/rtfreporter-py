# Releasing to PyPI

This page is for the **maintainer**.  The package is published as
[`rtfreporter`](https://pypi.org/project/rtfreporter/) by the GitHub Actions
workflow [`.github/workflows/release.yml`](https://github.com/ichirio/rtfreporter-py/blob/main/.github/workflows/release.yml),
with **PyPI Trusted Publishing** (OpenID Connect): PyPI trusts this repository's
workflow directly, so there is no API token to create, store or rotate, and
no secret in the repository.

| Trigger | Publishes to |
|---|---|
| Actions → **release** → *Run workflow* (`workflow_dispatch`) | **TestPyPI** (environment `testpypi`) |
| Publishing a **GitHub release** | **PyPI** (environment `pypi`) |

Both paths first build the sdist and wheel, run `twine check --strict`, install
the wheel into a clean virtual environment and import it.  A release also
checks that its tag (`v0.5.0`) matches `version` in `pyproject.toml`.

## One-time setup

Done once, by hand, by the maintainer.  Nothing here can be done from the
repository.

### 1. PyPI and TestPyPI accounts

1. Create an account on [pypi.org](https://pypi.org/account/register/) and,
   separately, on [test.pypi.org](https://test.pypi.org/account/register/)
   (they are independent services with independent accounts).
2. Verify the e-mail address on each.
3. Turn on **two-factor authentication** on each (*Account settings → Two
   factor authentication*; an authenticator app or a security key).  PyPI
   requires 2FA to publish.  Store the recovery codes safely.

### 2. A pending trusted publisher on each

The name `rtfreporter` is not taken yet, so the project is created by its
first upload.  A **pending** publisher reserves that right for this workflow.

On **PyPI**: *Your account → Publishing → Add a new pending publisher →
GitHub*, and enter exactly:

| Field | Value |
|---|---|
| PyPI Project Name | `rtfreporter` |
| Owner | `ichirio` |
| Repository name | `rtfreporter-py` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

On **TestPyPI** (test.pypi.org → *Your account → Publishing*), the same,
except **Environment name: `testpypi`**.

A pending publisher does not reserve the name against others until the
first upload, so do the first TestPyPI and PyPI uploads soon after.  After the
first upload it becomes an ordinary trusted publisher of the project.

### 3. The two GitHub environments

In the repository: *Settings → Environments → New environment*.

- **`testpypi`** -- no protection rules needed.
- **`pypi`** -- tick **Required reviewers** and add yourself (and any
  co-maintainer), so a release waits for an explicit approval before it is
  uploaded.  Optionally, under *Deployment branches and tags*, allow only
  tags matching `v*`.

The environment names must match the ones on PyPI / TestPyPI exactly, or the
upload is refused.

## Release checklist

1. **Version.**  Set the release version in **both** `pyproject.toml`
   (`version = "0.5.0"`) and `src/rtfreporter/__init__.py`
   (`__version__ = "0.5.0"`), dropping any `.devN`.
2. **Changelog.**  Rename `## [Unreleased]` in `CHANGELOG.md` to
   `## [0.5.0] — YYYY-MM-DD` and check its entries; update `CITATION.cff`'s
   version / date if it carries them.
3. **Checks on `main`.**  Merge the release PR; CI (`tests`, `package`) must be
   green.  Locally, if you like:

    ```bash
    ruff check . && pytest -q && mkdocs build --strict
    python -m build && twine check --strict dist/*
    ```

4. **TestPyPI dry run.**  *Actions → release → Run workflow* on `main`.  The
   `publish-testpypi` job uploads to TestPyPI.  A version can be uploaded only
   once to each index, so a second dry run needs a new version (for example
   `0.5.0rc1`, then `0.5.0rc2`).
5. **Install check** in a fresh virtual environment:

    ```bash
    python -m venv /tmp/rtf-test && . /tmp/rtf-test/bin/activate
    pip install -i https://test.pypi.org/simple/ rtfreporter
    python -c "import rtfreporter; print(rtfreporter.__version__)"
    ```

    The core has no dependencies.  To try an extra, let pip take its
    dependencies from PyPI:
    `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "rtfreporter[pandas]"`.
    Check the project page on test.pypi.org: the README renders, the links
    (Homepage, Documentation, Source, Issues, Changelog) work.
6. **Tag and release.**  Create a GitHub release with a new tag `v0.5.0`
   on `main` (*Releases → Draft a new release*), paste the changelog section as
   its notes, and **Publish release**.  The `publish-pypi` job waits for the
   `pypi` environment's approval; approve it and the package is uploaded to
   PyPI.
7. **After.**  Check <https://pypi.org/project/rtfreporter/> and
   `pip install rtfreporter`; then open the next development cycle
   (`0.5.1.dev0` or `0.6.0.dev0`) with a new `## [Unreleased]` section.

## If something goes wrong

- *"invalid-publisher" / "Trusted publishing exchange failure"*: the owner,
  repository, workflow file name or environment name on PyPI does not match
  the run.  Compare them with the table above.
- *"File already exists"*: that version is already on the index; versions
  cannot be replaced or re-used, even after deleting a release.  Bump the
  version.
- A bad release cannot be overwritten: **yank** it on PyPI (*Manage → Releases
  → Options → Yank*) and publish a fixed version.
