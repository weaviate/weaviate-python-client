### Setup

We recommend to create a virtual environment to contribute to the client.

Run the following to create a virtual environment, activate it and install dependencies:
```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-devel.txt
```

The next time you open your shell, you can activate your virtual environment using `source .venv/bin/activate`

To run local instance of Weaviate, we recommend using Docker (see https://weaviate.io/developers/weaviate/installation/docker-compose).

#### Installation

To install the library into your virtual environment while in development, we recommend installing it in “edit mode”:

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

> Note: We use [pytest](https://docs.pytest.org) to write tests, however many older tests use [unittest](https://docs.python.org/3/library/unittest.html). Regardless, the below commands will run all tests.

There are three kinds of tests:
- Unit tests, that test individual components of the client
- Integration tests, that test the client with a running weaviate instance
- Mock tests, where a weaviate instance is mocked to return specific replies

To run the integration tests,

1. Ensure that you have Docker installed, and then
2. Start the weaviate instances with:

```shell
./ci/start_weaviate.sh
```

Then run all tests with
```
pytest integration
pytest mock_tests
pytest test
```

### Linting

> **Note**
> We strongly recommend to use [pre-commit](https://pre-commit.com/) to automatically run all linters locally on each commit. Install on your system and then enable it using `pre-commit install`.

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

