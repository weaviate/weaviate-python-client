Local installation:

1. `python setup.py sdist`
2. `pip install .`

Publishing:

0. Ensure [twine](https://pypi.org/project/twine/) is installed (`pip install twine`).
1. Set the new version in the `weaviate/version.py` and `test/test_version.py`.
2. Run all tests (check [`test/README.md`](test/README.md)).
3. Then build the new package:\
`python setup.py sdist bdist_wheel`
4. And check it:\
`twine check dist/*`
5. Ensure you are on the correct **git branch**.
6. **Commit** and push the most current version to GitHub if this has not been done yet.
7. Check TravisCI status to be `OK!`. If not `OK!`, fix it.
8. Give the commit of the current version a proper tag:\
`git tag -a '<your tag>' -m '<some message for the tag>' && git push --tags`\
tags are either in the form of `v0.2.5` or `v0.2.5rc0`.
9. Optional: install package locally by running `pip install .` and check if the version is set correctly.
10. Finally publish:\
`twine upload dist/*`
