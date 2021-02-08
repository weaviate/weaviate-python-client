1. Set the new version in the `weaviate/version.py` and `test/test_version.py`.
2. Run all tests. (Check `test/README.md`)
3. Then build the new package:\
`python setup.py sdist bdist_wheel`
4. And check it:\
`twine check dist/*`
5. Check if you are on correct **GitBranch**.
6. **Commit** the most current version to GitHub if this has not been done yet.
7. Check TravisCI status to be `OK!`, if not `OK!` fix it.
8. Give the commit of the current version a proper tag:\
`git tag -a '<your tag>' -m '<some message for the tag>' && git push --tags`
tags are either in the form of `v0.2.5` or `v0.2.5rc0`.
9. Optional: install package locally by running `pip install .` and check if the version is set correctly.
10. Finally publish:\
`twine upload dist/*`
