### Setup

We recommend that you use a virtual environment to contribute to the client.

To create a virtual environment, activate it, and install dependencies, run the following shell code:

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-devel.txt
```

To activate your virtual environment, run `source .venv/bin/activate`.

The newest client versions sometimes require upcoming Weaviate core features. We recommend using Docker (see https://weaviate.io/developers/weaviate/installation/docker-compose) to run a local instance of the `latest Weaviate core <https://hub.docker.com/r/semitechnologies/weaviate/tags>`_ for client development. 

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


### Testing

> Note: We use [pytest](https://docs.pytest.org) to write tests for new client code. However, many older tests use [unittest](https://docs.python.org/3/library/unittest.html). These commands run the `pytest` and `unittest` tests.

There are three kinds of tests:
- Unit tests test individual client components.
- Integration tests use a running weaviate instance to test the client.
- Mock tests simulate a weaviate instance to return specific values.

To run the integration tests,

1. Ensure that you have Docker installed.
2. Start the weaviate instances, changing `WEAVIATE_VERSION` to your weaviate docker image target

```shell
./ci/start_weaviate.sh WEAVIATE_VERSION
```

3. Run the tests.

```
pytest integration
pytest mock_tests
pytest test
```

### Linting

> **Note**
> We strongly recommend using [pre-commit](https://pre-commit.com/) to automatically run all linters locally on each commit. Install `pre-commit` on your system, and then enable it with `pre-commit install`.

We use the following tools to ensure a high code quality:
- black (formatter), run with `black $FOLDER_WITH_CHANGES`
- flake8 with plugins. Run with `flake8 $FOLDER_WITH_CHANGES`. Note that all plugins are listed in the `requirements.txt` file and are installed in the first step.


### Creating a Pull Request

- The main branch is what is released and developed currently.
- You can create a feature-branch that is named: feature/YOUR-FEATURE-NAME.
- Your feature branch always has the main branch as a starting point.
- When you are done with your feature you should create a pull request into the main branch.
- The main branch is protected.

### Contributor License Agreement

Contributions to Weaviate python client must be accompanied by a Contributor License Agreement. You (or your employer) retain the copyright to your contribution; this simply gives us permission to use and redistribute your contributions as part of Weaviate Python client. Go to [this page](https://www.semi.technology/playbooks/misc/contributor-license-agreement.html) to read the current agreement.

The process works as follows:

- You contribute by opening a [pull request](#pull-request).
- If your account has no CLA, a DocuSign link will be added as a comment to the pull request.

