# Pending Updates

Changes to make later, with the moment each one becomes relevant.

## Build backend for `src/emporio/`

**When**: On creating the `src/emporio/` package, which is when a build system is first needed.

**Update**: [plan.md](../specs/001-streamlit-chat/plan.md) (Technical Context and Implementation Notes)
and [research.md](../specs/001-streamlit-chat/research.md) (section 10) specify hatchling. The developer
required changing this to setuptools.

**Findings**: Tested in a temporary project with uv 0.6.12:

- A build system is required because of the `src/` layout, not because of Streamlit. Without one, uv
  installs only the dependencies and `import emporio` fails, even with `__init__.py` in place.
- A `[tool.setuptools]` section alone is not enough, as the import still fails without `[build-system]`.
- Setuptools and hatchling both make the import work, and neither is installed in `.venv`.
- Setuptools finds `src/emporio` by itself but generates an `.egg-info` folder in `src/`, while hatchling
  generates none but needs its `packages` setting, because the project and package names differ.

**Change**: Add this to `pyproject.toml` and `*.egg-info/` to `.gitignore`:

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"
```

Then run `uv lock` and `make setup`.
