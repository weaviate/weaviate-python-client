====================================
Weaviate Python Client Documentation
====================================

This directory contain the library's documentation.

Add new modules/sub-packages to the documentation
-------------------------------------------------

All the pages of the documentation are contained in this folder and have the extension ``.rst``.

To add a new module/sub-packages just add another file with the name corresponding to its path. See the examples of the ``.rst`` files.
Add the newly created ``.rst`` page to the appropriate existing package.

For example is the new module has the path ``weaviate/new_module.py``, the new ``.rst`` file should be ``weaviate.new_module.rst``.
Then add ``weaviate.new_module`` to the ``weaviate.rst`` file, under the **Subpackages**, along with the existing sub-packages.

The ``.rst`` file can be generated using ``sphinx-apidoc --module-first -f -o . ../PATH_TO_THE_MODULE`` (for the case above ``PATH_TO_THE_MODULE=weaviate/new_module.py``).
You can edit the newly generated file to match the existing formats, or adjust it to your liking.

Also the ``.rst`` file can be created manually. You can get the inspiration from the existing modules/sub-packages ``.rst`` files.

Here is a link to a ``.rst`` `cheat sheet <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>`_.
Another useful information about ``sphinx.ext.autodoc`` can be found `here <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_.
For more information on ``Sphinx`` visit the official `website <https://www.sphinx-doc.org/en/master/index.html>`_.


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

