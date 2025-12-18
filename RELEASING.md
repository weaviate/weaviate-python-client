## How to create releases

### Step 1: Prepare for release
1. Pull latest main
	- Merge any pending PRs
2. Determine what the next version should be, following semantic versioning
3. Create a new branch for the changelog
4. Add a changelog entry to `docs/changelog.rst`
	- `gh pr list --repo weaviate/weaviate-python-client --state merged --search "merged:>=YYYY-MM-DD"` where `YYYY-MM-DD` is the last release date
	- Only add the relevant entries to the changelog
	- Examples - [minor release](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.18.0), [patch release](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.16.10)
5. Merge back to main
6. Pull main

### Step 2: Create release
Option 1: With GH CLI
1. `gh release create <VERSION_TAG>` (e.g. `gh release create v4.18.1`)

Option 2: With git + GH web UI
1. git tag VERSION
	- `git tag -a v4.18.1 -m "v4.18.1"
2. `git push --tags`
3. Create a release [from the GH repo](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository?tool=webui#creating-a-release)

### Step 3: Monitor pipeline
1. Monitor the CICD pipeline
	1. When all tests pass, the release will be pushed to PyPI automatically

### Notes:
- The package version is updated automatically (see setup.cfg)
