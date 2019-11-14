To publish a new documentation needs to be build:
`make -C documentation html`
Then build the new package:
`python setup.py bdist_wheel`
And check it:
`twine check dist/*`
Finally publish:
`twine upload dist/*`