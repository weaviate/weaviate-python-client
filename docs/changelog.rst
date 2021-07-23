Changelog
=========

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
