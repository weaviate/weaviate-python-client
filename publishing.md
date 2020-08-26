1. To publish a new documentation needs to be build:\
`make -C documentation html`
2. Make sure you set the right version in the `setup.py`
3. Then build the new package:\
`python setup.py bdist_wheel`
4. And check it:\
`twine check dist/*`
5. Check if you are on **Master** in case of full release.
6. **Commit** the most current version to GitHub if this has not been done yet.
7. Make sure you gave the commit of the current version a proper tag:\
`git tag -a '<your tag>' -m '<some message for the tag>' && git push --tags`
tags are either in the form of `0.2.5` or `0.2.5rc0`.
8. Finally publish:\
`twine upload dist/*`
9. After publishing change the version in `setup.py` to the next developement number.