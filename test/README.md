# Unit tests for Weaviate Python client
---
Unit tests for weaviate package. Each module should have its own sub-directory in the `test` directory. Each test file should begin with `test_<fine_name>.py` and `test` directory should not be renamed, these are mandatory requirements for the `unittest` to parse and run all unittests.

The `util.py` contains helper functions for unit testing.

---
## Run one file unittest
In order to unit test a single file you can run the following command:
```
python -m unittest path_to_file.file
```
E.g. if you run it from repo root folder:
```bash
python -m unittest test.gql.test_get -v # -v is optional, -v = verbose
```
## Run one module/whole package unittest
In order to unit test a single module you can run the following command:
```
python -m unittest path_to_module.module
```
E.g. if you run it from repo root folder for a module:
```bash
python -m unittest test.gql -v # -v is optional, -v = verbose
```
E.g. if you run it from repo root folder for the whole package:
```bash
python -m unittest -v # -v is optional, -v = verbose
```