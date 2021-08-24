Changelog
=========

Version 3.1.1
-------------

- Fixes in :class:`~weaviate.wcs.WCS` class:
    - | Make :class:`~weaviate.wcs.WCS`'s methods' argument ``cluster_name`` case insensitive (lowercased inside the method) to match Weaviate Cloud Service'
        naming convention, this fixes the error when Weaviate Cloud Service lowercases the ``cluster_name`` but the users are not aware of this and get the exception
        `KeyError`. 

Version 3.1.0
-------------

- New :class:`~weaviate.batch.Batch` methods:
    - | :meth:`~weaviate.batch.Batch.pop_object` / :meth:`~weaviate.batch.Batch.pop_reference` to remove and return an added object/reference
        from the :class:`~weaviate.batch.Batch` at position ``index`` (by default ``-1``).
    - |  :meth:`~weaviate.batch.Batch.empty_objects` / :meth:`~weaviate.batch.Batch.empty_references` to remove all the existing objects/references
        from the :class:`~weaviate.batch.Batch` instance.
    - |  :meth:`~weaviate.batch.Batch.is_empty_objects` / :meth:`~weaviate.batch.Batch.is_empty_references` to check there are any objects/references
        in the :class:`~weaviate.batch.Batch` instance.
- Fixes in :class:`~weaviate.wcs.WCS` class:
    - Authentication only with :class:`~weaviate.auth.AuthClientPassword`.
    - | The :meth:`~weaviate.wcs.WCS.create` argument ``module`` is renamed to ``modules`` and can also be a list of modules to enable for the WCS cluster.
        The argument can be used on the `PROD <https://console.semi.technology/>`_ WCS too.
    - The :meth:`~weaviate.wcs.WCS.get_cluster_config` does not raise an exception if the cluster does not exist but returns a empty configuration.
    - The :meth:`~weaviate.wcs.WCS.delete_cluster` does not raise an exception if the cluster does not exist.

- Add ``phoneNumber`` to the Weaviate's primitive types. Thanks to GitHub user `@cdpierse <https://github.com/cdpierse>`_.
- Bug fix in :class:`~weaviate.connect.Connection`.
- Fix ``ConnectionError`` handling.
- Optimization in ``weaviate.batch.requests`` and ``weaviate.connect.connection``.


Version 3.0.0
-------------

- ``weaviate.tools`` module is REMOVED.
    - ``Batcher`` class is REMOVED.
    - ``WCS`` class is moved from the ``weaviate.tools`` to the new module ``weaviate.wcs``
    - ``weaviate.tools.generate_uuid`` is REMOVED.
- :func:`weaviate.util.generate_uuid5` is ADDED.
- | New :class:`~weaviate.batch.Batch` class implementation to replace the old one. This implementation uses the ``BatchRequest`` 
    objects under the hood, which means that there is no need to create ``BatchRequest``'s anymore. This new class implementation
    allows 3 different batch creations methods: `manual`, `auto-create` and `auto-create` with dynamic batching.
    See the :class:`~weaviate.batch.Batch` documentation for more information.
- | ``BatchRequest`` classes (``ObjectsBatchRequest`` and ``ReferenceBatchRequest``) are hidden from the user and should not be
    used anymore. This is due to the new :class:`~weaviate.batch.Batch` class implementation.
- | New :class:`~weaviate.schema.Schema` field is ADDED, `"shardingConfig"`. It can bu used with Weaviate version >= 1.6.0.
- | New method :meth:`~weaviate.schema.Schema.update_config` used to update mutable schema configuration (like `efConstruction`, ...).
