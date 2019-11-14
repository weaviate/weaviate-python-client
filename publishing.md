1. To publish a new documentation needs to be build:\
`make -C documentation html`\
2. Make sure you set the right version in the `setup.py`
3. Then build the new package:\
`python setup.py bdist_wheel`\
4. And check it:\
`twine check dist/*`\
5. Commit the most current version to GitHub if this has not been done yet.
6. Make sure you gave the commit of the current version a proper tag:\
`git tag -a '<your tag>' -m '<some message for the tag>' && git push --tags`\
Finally publish:\
`twine upload dist/*`\