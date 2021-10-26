Changelog
=========

Version 3.2.5
-------------
This patch fixes the ``'Batch' object is not callable`` error.

Version 3.2.4
-------------
| All ``class_name`` and cross-refs ``dataType`` are implicitly capitalized. (This functionality is added because if ``class_name`` is not capitalized
    then Weaviate server does it for you, and this was leading to errors where the client and server have different configurations.)

Fixes/updates in :class:`~weaviate.schema.crud_schema.Schema` class:

- | This patch fixes the :meth:`~weaviate.schema.crud_schema.Schema.contains` to accept separate class schemas as argument
    i.e. it does not expect to have only this format: ``{"classes": [CLASS_1, CLASS_2, ...]}``; now it is possible to pass just ``CLASS_X`` as well.

Version 3.2.3
-------------
This patch fixes the :meth:`~weaviate.gql.get.GetBuilder.with_near_object`. It uses now explicit string literals for ``id``/``beacon`` in `nearoOject` clauses.

Version 3.2.2
-------------
This patch adds support for `array` data types: ``boolean[]``, ``date[]``.

Version 3.2.1
-------------
This patch adds support for `array` data types: ``int[]``, ``number[]``, ``text[]``, ``string[]``.

Version 3.2.0
-------------

Fixes/updates in :class:`~weaviate.wcs.WCS` class:

- Fixed progress bar for :meth:`~weaviate.wcs.WCS.create`, it is being updated in Notebooks too, instead of printing each iteration on new line.
- Method :meth:`~weaviate.wcs.WCS.create` now prints the creation status above the bar.

Updates in :mod:`~weaviate.gql` sub-package:

- | New key-value ``autocorrect: <bool>`` introduced for the :class:`~weaviate.gql.filter.NearText` and :class:`~weaviate.gql.filter.Ask` filters.
    The ``autocorrect`` is enabled only if Weaviate server has the ``text-spellcheck`` module enabled. If ``autocorrect`` is ``True`` the query is
    corrected before the query is made. Usage example:

.. code-block:: python

    # with 'nearText' filter
    client.query\
        .get('Article', ['title', 'author'])\
        .near_text(
            {
                'concepts': ['Ecconomy'],
                'autocorrect': True
            }
        )
        # the concept should be corrected to 'Economy'
    # with 'ask' filter
    client.query\
        .get('Article', ['title', 'author'])\
        .with_ask(
            {
                'question': 'When was the last financial crysis?',
                'autocorrect': True
            }
        )
        # the question should be corrected to 'When was the last financial crisis?'

- | New method :meth:`~weaviate.gql.get.GetBuilder.with_additional` is added to GET the `_additional` properties. Usage example:

.. code-block:: python

    # single additional property with this GraphQL query
    '''
    {
        Get {
            Article {
                title
                author
                _additional {
                    id
                }
            }
        }
    }
    '''
    client.query\
        .get('Article', ['title', 'author'])\
        .with_additional('id') # argument as `str`

    # multiple additional property with this GraphQL query
    '''
    {
        Get {
            Article {
                title
                author
                _additional {
                    id
                    certainty
                }
            }
        }
    }
    '''
    client.query\
        .get('Article', ['title', 'author'])\
        .with_additional(['id', 'certainty']) # argument as `List[str]`

    # additional properties as clause with this GraphQL query
    '''
    {
        Get {
            Article {
                title
                author
                _additional {
                    classification {
                        basedOn
                        classifiedFields
                        completed
                        id
                        scope
                    }
                }
            }
        }
    }
    '''
    client.query\
        .get('Article', ['title', 'author'])\
        .with_additional(
            {
                'classification' : [
                    'basedOn',
                    'classifiedFields',
                    'completed',
                    'id',
                    'scope'
                ]
            }
        ) # argument as `Dict[str, List[str]]`

    # or with this GraphQL query
    '''
    {
        Get {
            Article {
                title
                author
                _additional {
                    classification {
                        completed
                    }
                }
            }
        }
    }
    '''
    client.query\
        .get('Article', ['title', 'author'])\
        .with_additional(
            {
                'classification' : 'completed'
            }
        ) # argument as `Dict[str, str]`

    # additional properties as clause and clause settings with this GraphQL query
    '''
    {
        Get {
            Article {
                title
                author
                _additional {
                    token (
                        properties: ["content"]
                        limit: 10
                        certainty: 0.8
                    ) {
                        certainty
                        endPosition
                        entity
                        property
                        startPosition
                        word
                    }
                }
            }
        }
    }
    '''
    clause = {
        'token': [
            'certainty',
            'endPosition',
            'entity',
            'property',
            'startPosition',
            'word',
        ]
    }
    settings = {
        'properties': ["content"],  # is required
        'limit': 10,                # optional, int
        'certainty': 0.8            # optional, float
    }
    client.query\
        .get('Article', ['title', 'author'])\
        .with_additional(
            (clause, settings)
        ) # argument as `Tuple[Dict[str, List[str]], Dict[str, Any]]`

    # if the desired clause does not match any example above, then the clause can always
    # be converted to string before passing it to the `.with_additional` method


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


