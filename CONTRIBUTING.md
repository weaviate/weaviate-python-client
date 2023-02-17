### Setup

We recommend to create a virtual environment to contribute to the client. You can install all developer dependencies using `pip install requirements.txt`.

### Testing

We use [pytest](https://docs.pytest.org) to write tests, however there are plenty of older tests that use unittest.

There are three kinds of tests:
- Unit tests, that test individual components of the client
- Integration tests, that test the client with a running weaviate instance
- Mock tests, where a weaviate instance is mocked to return specific replies

To run the integration tests start the weaviate instances using `./ci/start_weaviate.sh`.
Then run all tests with
```
pytest integration
pytest mock_tests
pytest test
```

### Linting

We use the following tools to ensure a high code quality:
- black (formatter)
- flake8 with plugins

To avoid annoying CI failures we use [pre-commit](https://pre-commit.com/) to automatically run all linters locally on each commit.

### Creating a Pull Request

- The main branch is what is released and developed currently.
- You can create a feature-branch that is named: feature/YOUR-FEATURE-NAME.
- Your feature branch always has the main branch as a starting point.
- When you are done with your feature you should create a pull request into the main branch.
- The main branch is protected.

### Contributor License Agreement

Contributions to Weaviate Go client must be accompanied by a Contributor License Agreement. You (or your employer) retain the copyright to your contribution; this simply gives us permission to use and redistribute your contributions as part of Weaviate Go client. Go to [this page](https://www.semi.technology/playbooks/misc/contributor-license-agreement.html) to read the current agreement.

The process works as follows:

- You contribute by opening a [pull request](#pull-request).
- If your account has no CLA, a DocuSign link will be added as a comment to the pull request.

