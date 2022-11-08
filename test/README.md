# Unit tests for Weaviate Python client
---
Unit tests for weaviate package. Each module should have its own sub-directory in the `test` directory. Each test file should begin with `test_<fine_name>.py` and `test` directory should not be renamed, these are mandatory requirements for the `unittest` to parse and run all unittests.

The `util.py` contains helper functions for unit testing.

---
## Run one file unittest
In order to unit test a single file, you can run the following command:
```
python -m unittest path_to_file_dir.file
```
E.g. if you run it from repo root folder:
```bash
python -m unittest test.gql.test_get -v # -v is optional, -v = verbose
```
## Run whole package unittest
In order to unit test the whole package, you can run the following command:
```bash
python -m unittest -v # -v is optional, -v = verbose
```

# Coverage test
---
Coverage test for weaviate package. Coverage test can be performed using the existing unit test. It runs all the unit tests in order to find which parts of the code have been executed, thus it can be used instead of the Unit test.
Coverage test is performed by the `coverage` package that should be installed with the `development-requirements.txt`. For more information on what and how to run coverage tests visit this [link](https://coverage.readthedocs.io/en/coverage-5.3.1/ "coverage.readthedocs.io").

---

## Run coverage test for one file
Coverage test for one file can be performed using the following command:
```bash
coverage run -m unittest path_to_the_file_dir.file -v # -v is optional, -v = verbose
```
E.g. if you run it from repo root folder:
```bash
coverage run -m unittest test.gql.test_get -v # -v is optional, -v = verbose
```

## Run whole package coverage test
In order to unit test the whole package, you can run the following command:
```bash
coverage run -m unittest -v # -v is optional, -v = verbose
```
## Show coverage report
To get the coverage report run the following command.
```bash
coverage report -m --skip-covered # --skip-covered = skip 100% covered files, -m = show missing lines
```

# Linting
---
Lint the files that are modified before commiting. The linting is done by `pylint`.

To lint a file/module/package run the following command:
```bash
pylint path_to_the_file_or_module
```
E.g. if you run it from repo root folder:
```bash
pylint weaviate # for the whole package
pylint weaviate/batch # for the module batch
pylint weaviate/connect/connection.py # for the connection.py file
```
