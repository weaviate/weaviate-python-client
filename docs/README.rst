====================================
Weaviate Python Client Documentation
====================================

This directory contain the library's documentation. It is published on `Read the Docs <https://weaviate-python-client.readthedocs.io/en/stable/>`_
using the Sphinx documentation engine. More about Sphinx engine and how it works can be found here `Sphinx <https://www.sphinx-doc.org/en/master/index.html>`_.

NOTE: Current setup does not add all the modules/sub-packages to the documentation automatically it needs to be set explicitly.
All the new modules/sub-packages that are needed to be part ReadTheDocs documentation need to be added manually.

NOTE2: This documentation is useing the `weaviate-agents-python-client` package and publishes both documentations as a single ReadTheDocs page.
The `weaviate-agents` package is a sub-package of the `weaviate-python-client` package. This means that any changes of the Weaviate Agents
Python Client will not be reflected right away, it will be update either on a new release of the `weaviate-python-client` or can be triggered
manually from the readthedocs page directly (maintained by the Weaviate Python Client team).
The documentation of the `weaviate-agents-python-client` repo is cloned in the `build` step of the `.readthedocs.yaml` file.

Adding and Modifying new modules/sub-packages
---------------------------------------------

Sphinx `autodoc-api` extension is used to generate the documentation from the docstrings in the source code. You can use it to generate the documentation for the
new modules/sub-packages. The way it works is by generating `***.rst` files  **ONLY** for sub-packages, that also includes the sub-package's modules. The `***.rst`
files are then included in the corresponding parent (sub-)package. The `index.rst` is the root file and the first page of the ReadTheDocs documentation.

EXAMPLE: Lets say that we have the following structure:

.. code-block:: bash

    weaviate/
    ├── __init__.py
    ├── client.py
    ├── sub_package1/
    │   ├── __init__.py
    │   ├── module1.py
    ├── sub_package2/
        ├── __init__.py
        ├── module2.py
        ├── sub_sub_package3/
            ├── __init__.py
            ├── module3.py


For the above structure, the `autodoc-api` will generate the following `***.rst` files:
- |
    `weaviate.rst` which is the root package and it should contain the imediate childeren sub-packages, which in this case are `sub_package1` and `sub_package2`,
    along with the `client.py` module.
- `weaviate.sub_package1.rst` which should contain the `module1.py` module.
- `weaviate.sub_package2.rst` which should contain the `module2.py` module and the `sub_sub_package3` sub-package.
- `weaviate.sub_package2.sub_sub_package3.rst` which should contain the `module3.py` module.

In order to generate the `***.rst` files run the following command:
.. code-block:: bash

    sphinx-apidoc --module-first  -o ./docs ./weaviate "*proto*" # `"*proto*"` is used to exclude the `weaviate/proto` package

This command will create all the new packages and thier corresponding modules but it will not add them to the parent pages. You need to do
that manually.

If you have only a new module that was added to the existing package, you can manually modify the corresponding the `***.rst` file for that
sub-package. You can look at the existing `***.rst` files for the reference.

NOTE: Feel free to modify the generated `***.rst` files as needed.

Pre-processing the documentation
--------------------------------

Sphinx also offers the possibitity to pre-processing the documentation. This can be done by using the `conf.py` file. The `conf.py` file is located in the `docs` directory.
It can be use to change a specific class docstring or all at once. For example now it uses a pre-processing function to change all Markdown links to reStructuredText links,
so that the links are correctly rendered in the documentation but the links are still in Markdown format in the source code.

It is also possible to set default configurations for the `sphinx-apidoc` command in the `conf.py` file. For example, the `sphinx-apidoc` command can be set to exclude
specific packages or modules by default.


Make the documentation locally
------------------------------

| The documentation can be built locally in different formats like ``html``, ``latex``, ...
| In order to build the HTML documentation locally run:

.. code-block:: bash

    make html # from the 'docs' directory

| The HTML files can be found in the generated `_build` directory.
| If you want to view the HTML documentation run the following command:

.. code-block:: bash

    open _build/html/index.html # from the 'docs' directory

