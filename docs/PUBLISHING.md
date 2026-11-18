# Documentation Publishing

How the reference docs at https://weaviate-python-client.readthedocs.io/ are built, how the `weaviate-agents-python-client` is folded in, and how to publish a staging preview for a branch.

For authoring guidance (adding modules, regenerating `.rst` files, building locally), see [README.rst](./README.rst).

## What publishes the docs

Read the Docs (RTD), not GitHub Actions. RTD is configured to watch this repo and rebuild on every push to a tracked branch or tag. The CI workflow at `.github/workflows/main.yaml` only runs `python -m sphinx ...` as a sanity check — it never publishes anything.

Project dashboard: https://readthedocs.org/projects/weaviate-python-client/

## Build configuration

Two files control the build:

- **`.readthedocs.yaml`** — RTD build config (Python version, `pre_build` hooks, requirements file, Sphinx entry point).
- **`docs/conf.py`** — Sphinx config (extensions, theme, autodoc behavior, docstring post-processing).

Build steps RTD runs, in order:

1. Spin up an Ubuntu 22.04 image with Python 3.12 (per `.readthedocs.yaml`).
2. Run the `pre_build` hook (see next section — this is where the agents client gets pulled in).
3. `pip install -r requirements-devel.txt`.
4. `python -m sphinx -b html docs/ <output>` using `docs/conf.py`.
5. Publish the HTML to `https://weaviate-python-client.readthedocs.io/en/<version-slug>/`.

## How the agents client is folded in

The `weaviate-agents-python-client` lives in its own repo (https://github.com/weaviate/weaviate-agents-python-client) but its API reference is published as part of the same RTD site.

This is wired up in `.readthedocs.yaml` via a `pre_build` hook:

```yaml
build:
  jobs:
    pre_build:
      - git clone -b main --depth=1 https://github.com/weaviate/weaviate-agents-python-client.git docs/weaviate-agents-python-client
      - python -m pip install -e ./docs/weaviate-agents-python-client
```

And `docs/conf.py` adds the cloned directory to `sys.path`:

```python
sys.path.insert(0, os.path.abspath("weaviate-agents-python-client"))
```

Implications:

- The agents docs always come from the agents repo's `main` branch — pinning to a tag would require editing `.readthedocs.yaml`.
- Changes merged to the agents repo's `main` are **not** automatically published here. The published version updates when either (a) a new release of `weaviate-python-client` is cut, or (b) a maintainer manually triggers a rebuild from the RTD dashboard.
- The agents repo has its own `docs/` tree (with its own `index.rst`, etc.). After cloning, RTD's Sphinx build picks up those `.rst` files because they sit under `docs/weaviate-agents-python-client/docs/`, which Sphinx walks as part of the source tree.

## Publishing a staging build for a branch

Add the branch as a Version in RTD:

1. Open https://readthedocs.org/projects/weaviate-python-client/versions/.
2. Click **+ Add version**, pick the branch from the dropdown (hit the refresh icon if it's not listed yet — RTD polls GitHub for new branches).
3. Tick **Active**. Leave **Hidden** ticked if you don't want the branch to show up in the version switcher on the public site (you'll still get a direct URL).
4. Click **Update version**. RTD kicks off a build immediately.

Watch the build on the **Builds** tab. Once it succeeds, the preview is at:

```
https://weaviate-python-client.readthedocs.io/en/<branch-slug>/
```

RTD slugifies the branch name — slashes become dashes (e.g. `docs/suppress-overload-stacking` → `docs-suppress-overload-stacking`).

When you're done, deactivate the version on the same page so it stops rebuilding on every push to that branch.
