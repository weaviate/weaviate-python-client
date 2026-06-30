### Setup

The development requirements are listed in the `requirements-devel.txt` file. Install them to your virtual environment with:

```shell
pip install -r requirements-devel.txt
```

The newest client versions sometimes require upcoming Weaviate core features. We recommend using Docker (see https://docs.weaviate.io/deploy/installation-guides/docker-installation) to run a local instance of the [latest Weaviate core](https://hub.docker.com/r/semitechnologies/weaviate/tags) for client development.

#### Installation

To install a development version of the Python client library in your virtual environment, use “edit mode”:

```shell
pip install -e /PATH/TO/WEAVIATE-PYTHON-CLIENT
```

If you do so from the root of the repository, you can use the following command:

```shell
pip install -e .
```

You can install a particular branch directly from GitHub with:

```shell
pip install git+https://github.com/weaviate/weaviate-python-client.git@BRANCH_NAME
```

If any static analysis tools such as Pylance fail, try installing the package with:
`--config-settings editable_mode=compat` suffix. (e.g. `pip install -e . --config-settings editable_mode=compat`)

### Project structure

The client is organized around the v4 collections API. When adding or updating code, prefer the existing v4-style collection interfaces rather than the legacy v3 client patterns.

Commonly changed areas include:

- `weaviate/collections/` for the v4 collection APIs and typed request/response classes.
- `weaviate/connect/` for connection and transport behavior.
- `test/` for unit tests that do not require a running Weaviate instance.
- `mock_tests/` for tests that simulate Weaviate responses.
- `integration/` for tests that require a local Weaviate instance.

### Testing

To set up the testing environment, install the test requirements with:

```shell
pip install -r requirements-test.txt
```

There are three kinds of tests:
- Unit tests test individual client components.
- Integration tests use a running Weaviate instance to test the client.
- Mock tests simulate a Weaviate instance to return specific values.

For most pull requests, run the smallest relevant test target first, for example:

```shell
pytest test/path_to_changed_test.py
pytest mock_tests/path_to_changed_test.py
```

To run the full local test groups:

```shell
pytest test
pytest mock_tests
```

To run the integration tests:

1. Ensure that you have Docker installed.
2. Start the Weaviate instances, changing `WEAVIATE_VERSION` to your Weaviate Docker image target.

```shell
./ci/start_weaviate.sh WEAVIATE_VERSION
```

3. Run the tests.

```shell
pytest integration
```

### Linting

> **Note**
> We strongly recommend using [pre-commit](https://pre-commit.com/) to automatically run all linters locally on each commit. Install `pre-commit` on your system, and then enable it with `pre-commit install`.

We use the following tools to ensure a high code quality:
- ruff (formatter), run with `ruff format $FOLDER_WITH_CHANGES`
- flake8 with plugins. Run with `flake8 $FOLDER_WITH_CHANGES`.

Note that all plugins are listed in the `requirements-devel.txt` file and are installed in the first step.

Before opening a pull request, run the linters on the files you changed:

```shell
ruff format $FOLDER_WITH_CHANGES
ruff check $FOLDER_WITH_CHANGES
flake8 $FOLDER_WITH_CHANGES
```

### Creating a Pull Request

- The main branch is what is released and developed currently.
- Create a focused branch from `main`, for example `feature/YOUR-FEATURE-NAME`, `fix/YOUR-BUG-FIX`, or `docs/YOUR-DOCS-UPDATE`.
- Keep the pull request focused on one change and include tests or documentation updates when relevant.
- Run the relevant tests and linters before requesting review.
- Create the pull request into the main branch.
- The main branch is protected.

### Contributor License Agreement

Contributions to Weaviate python client must be accompanied by a Contributor License Agreement. You (or your employer) retain the copyright to your contribution; this simply gives us permission to use and redistribute your contributions as part of Weaviate Python client. Go to [this page](https://www.semi.technology/playbooks/misc/contributor-license-agreement.html) to read the current agreement.

The process works as follows:

- You contribute by opening a [pull request](#creating-a-pull-request).
- If your account has no CLA, a DocuSign link will be added as a comment to the pull request.
