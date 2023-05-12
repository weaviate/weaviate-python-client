Changelog
=========

Version 3.18.0
--------------

This minor version includes:

- Add support for properties with hybrid search
- Fixes documentation publishing on readthedocs

Version 3.17.1
--------------
This patch version includes:

- Fix schemas with new property keys `indexFilterable` and `indexSearchable`.

Version 3.17.0
--------------
This minor version includes:

- Add support for groupBy to group objects:
    .. code-block:: python

           .with_group_by(properties=["caller"], groups=2, objects_per_group=3)


- Add support for `uuid` and `uuid[]` datatypes.
- Add `schema.exists(class)`.
- Add support for `Support GQL Get{} tunable consistency`
    .. code-block:: python

        resp = (
            client.query.get("Article", ["name"])
            .with_additional("isConsistent")
            .with_consistency_level(ConsistencyLevel.ALL)
            .do()
        )

Version 3.16.2
--------------
This patch version includes:

- Fix `url` containing username and password.

Version 3.16.1
--------------
This patch version includes:

- Fixes timeout error in detection of grpc.

Version 3.16.0
--------------
This minor version includes:

- **Experimental** support for GRPC.
    - Can by enabled by installing the client with `pip install weaviate-client[GRPC]` or install the `grpcio` package manually.
    - To disable uninstall the `grpcio` package.
    - This will speed up certain GraphQL queries: `Get` with `NearObject` or `NearVector` if only non-reference queries are retrieved and no other options are set.

- Removal of python 3.7 support. Minimum supported version is python 3.8
- Removal of the WCS module. Note that the module was used to administrate old WCS instances and does not work anymore.

Version 3.15.6
--------------
This patch version includes:

- Fix multi-line queries for BM25 and hybrid search.


Version 3.15.5
--------------
This patch version includes:

- EmbeddedDB now supports ``latest`` and versions (eg ``1.18.3``) as ``version`` argument.
- Removed ``cluster_hostname`` from ``EmbeddedOptions``. It can still be set by using ``additional_env_vars``.
- Fix multi-line queries for generative search.

Version 3.15.4
--------------
This patch version includes:

- Fix imports of EmbeddedDB on Mac. It now properly raises an exception that MacOS is currently unsupported.


Version 3.15.3
--------------
This patch version includes:

- Improve embedded weaviate: Better folder structures, add support for env variables and support multiple versions.
- Fix edge case for timeout retries: When all objects have been added, no empty batch will be send.
- Fix authentication via additional_headers

Version 3.15.2
--------------
This patch version includes:

- Fixes API keys with Weaviate setups that do not have OIDC enabled.

Version 3.15.1
--------------
This patch version includes:

- Fixes refreshing of OIDC tokens on unstable connections


Version 3.15.0
--------------
This minor version includes:

- GraphQL Multiple queries and aliases support
    .. code-block:: python

        client.query.multi_get(
                [
                   client.query.get("Ship", ["name"]).with_alias("one"),
                   client.query.get("Ship", ["size"]).with_alias("two"),
                   client.query.get("Person", ["name"])
                ]
- Adds support for embedded weaviate version
    .. code-block:: python

        from weaviate import Client
        from weaviate.embedded import EmbeddedOptions

        # Create the embedded client which automatically launches a Weaviate database in the background
        client = Client(embedded_options=EmbeddedOptions())


Version 3.14.0
--------------
This minor version includes:

- Support for API-Keys
    .. code-block:: python

        client = weaviate.Client(url, auth_client_secret=AuthApiKey(api_key="my-secret-key"))

Version 3.13.0
--------------
This minor version includes:

- Extend CRUD operations for single data objects and reference with consistency level.

- Extend batch operations with consistency level.

- Add Cursor api.

- Add support for azure backup module.

Version 3.12.0
--------------
This minor version includes:

- Adds with_generate in :meth:`~weaviate.gql.get.GetBuilder` which allows to use the generative openai module. Needs Weaviate with version >=v1.17.3.

- Fix for empty OIDC scopes

- New startup_period parameter in :meth:`~weaviate.client.Client`. The client will wait for the given timeout for
  Weaviate to start. By default 5 seconds.

- Improved error messages for where filters and authentication.

Version 3.11.0
--------------
This minor version includes:

- New status code attribute for :class:`~weaviate.exceptions.UnexpectedStatusCodeException` that can be accessed like this:

    .. code-block:: python

        try:
            # your code
        except weaviate.UnexpectedStatusCodeException as err:
            print(err.status_code)

- Fix for :meth:`~weaviate.client.Client.get_meta`.

- Caches server version at :class:`~weaviate.client.Client` initialization. This improves batch reference creation performance.

- Changes accepted data types for arguments ``from_object_uuid`` and ``to_object_uuid``  of the method :meth:`~weaviate.batch.Batch.add_reference` to ``str`` and ``uuid.UUID``.

- |
    Adds automatic retry for failed objects. It can be configured using the ``weaviate_error_retries`` argument for the :meth:`~weaviate.batch.Batch.configure` or
     :meth:`~weaviate.batch.Batch.__call__`, and should be an instance of :class:`~weaviate.WeaviateErrorRetryConf`. It can be used like this:

    - All errors:

        .. code-block:: python

            from weaviate import WeaviateErrorRetryConf

            with client.batch(
                weaviate_error_retries=WeaviateErrorRetryConf(number_retries=3),
            ) as batch:
                # Your code

    - Exclude errors, all the other errors will be retried:

        .. code-block:: python

            from weaviate import WeaviateErrorRetryConf

            with client.batch(
                weaviate_error_retries=WeaviateErrorRetryConf(number_retries=3, errors_to_exclude=["Ignore me", "other error to ignore"]),
            ) as batch:
                # Your code

    - Include errors, all the other errors will be ignored:

        .. code-block:: python

            from weaviate import WeaviateErrorRetryConf

            with client.batch(
                weaviate_error_retries=WeaviateErrorRetryConf(number_retries=3, errors_to_include=["error to retry", "other error to test again"]),
            ) as batch:
                # Your code

- Adds new arguments ``sort`` and ``offset`` for :meth:`~weaviate.data.DataObject.get`.


Version 3.10.0
--------------
This minor version includes:

- Improves error message for error ``"413: Payload Too Large"``
- |
    Adds new :class:`~weaviate.client.Client` credential OIDC flow method:

        .. code-block:: python

            client_credentials_config = weaviate.AuthClientCredentials(
                client_secret = "client_secret",
                scope = "scope1 scope2" # optional, depends on the configuration of your identity provider
            )
            client = weaviate.Client("https://localhost:8080", auth_client_secret=client_credentials_config)
- Improves size of batches on dynamic batching.
- New ``limit`` argument to :meth:`~weaviate.data.DataObject.get` method of the :class:`~weaviate.data.DataObject` client attribute.
- Bump minimum version of request to ``2.28.0``
- |
    Adds support for ``node_name`` and ``consistency_level`` for both :meth:`~weaviate.data.DataObject.get` and :meth:`~weaviate.data.DataObject.get_by_id`
    of the :class:`~weaviate.data.DataObject` client attribute.
    This can be used `ONLY` with Weaviate Server ``v1.17.0`` or later.
- |
    Adds support for replication factor in schema. This can be used `ONLY` with Weaviate Server ``v1.17.0`` or later. This can be configured in class schema like this:

        .. code-block:: python

            my_class = {
                "class": "MyClass",
                ...,
                "replicationConfig": {
                    "factor": 1
                }
            }
- Adds support for ``Bm25`` for ``Get`` queries, :meth:`~weaviate.gql.get.GetBuilder.with_bm25`. This can be used `ONLY` with Weaviate Server ``v1.17.0`` or later.
- Adds support for ``with_hybrid`` for ``Get`` queries, :meth:`~weaviate.gql.get.GetBuilder.with_hybrid`. This can be used `ONLY` with Weaviate Server ``v1.17.0`` or later.


Version 3.9.0
-------------
This minor version includes:


- Authentication using Bearer token, by adding ``additional_headers`` to the :class:`~weaviate.client.Client` initialization:
    .. code-block:: python

        client = weaviate.Client(
            url='http://localhost:8080',
            additional_headers={
                {"authorization": "Bearer <MY_TOKEN>"}
            }
        )

- Multi-threading :class:`~weaviate.batch.Batch`  import:
    - |
        Now it is possible to import data using multi-threading. The number of threads can be set using the new argument ``num_workers`` in
        :meth:`~weaviate.batch.Batch.configure` and :meth:`~weaviate.batch.Batch.__call__`, defaults to `1` ( Use with care to not overload your weaviate instance.).
    - |
        New argument ``connection_error_retries`` to retry on ``ConnectionError`` that can be set in :meth:`~weaviate.batch.Batch.configure` and :meth:`~weaviate.batch.Batch.__call__`
        or using the property getter/setter: ``client.batch.connection_error_retries`` to get the value and ``client.batch.connection_error_retries = 5`` to set the value.
    - |
        New method :meth:`~weaviate.batch.Batch.start` to create a ``BatchExecutor`` (``ThreadExecutor``). This method does NOT need to be called if using the
        :class:`~weaviate.batch.Batch` in a context manager (``with``). Also it is idempotent.
    - |
        New method :meth:`~weaviate.batch.Batch.shutdown` to shutdown the existing ``BatchExecutor`` (``ThreadExecutor``) to release any resources that it is holding once the
        batch import is done. This method does NOT need to be called if using the :class:`~weaviate.batch.Batch` in a context manager (``with``). Also it is idempotent.

- New :class:`~weaviate.client.Client` attribute :class:`~weaviate.cluster.Cluster` to check the status of the cluster nodes.
    - The method :meth:`~weaviate.cluster.Cluster.get_nodes_status` returns the status of each node as a list of dictionaries.
        .. code-block:: python

            client.cluster.get_nodes_status()

- Fix for :meth:`~weaviate.data.DataObject.replace` and :meth:`~weaviate.data.DataObject.update` when using with Weaviate server ``>=v1.14.0``.

- New default ``timeout_config``: ``(10, 60)``.

Version 3.8.0
-------------
This minor version includes:

- Backup functionalities (:class:`~weaviate.backup.Backup`):
    - :meth:`~weaviate.backup.Backup.create` method to create backups (all/subset of classes).
    - :meth:`~weaviate.backup.Backup.get_create_status` method to get the status of the created backup.
    - :meth:`~weaviate.backup.Backup.restore` method to restore Weaviate from a backup (all/subset of classes).
    - :meth:`~weaviate.backup.Backup.get_restore_status` method to get the status of the restored backup.
- New :class:`~weaviate.Client` attribute: ``backup`` to ``create``, ``restore`` and ``get status`` of the backups. All backup operations MUST be done through ``Client.backup``.
- Added return value for :meth:`~weaviate.batch.Batch.add_data_object`, it now returns the UUID of the added object, if one was not set then an UUIDv4 will be generated.

Version 3.7.0
-------------
This minor version includes:

- Adds rolling average (last 5 batches) for batch creation time used by Dynamic Batching method.
- Adds ability to use :meth:`~weaviate.gql.Query.get` without specifying any properties IF Additional Properties (:meth:`~weaviate.gql.get.GetBuilder.with_additional`) are set before executing the query.
- Adds base Weaviate Exception :class:`~weaviate.exceptions.WeaviateBaseError`.
- Adds ability to set proxies. Can be set at :class:`~weaviate.client.Client` initialization by using the new ``proxies`` or ``trust_env`` arguments.
- :class:`~weaviate.batch.crud_batch.Batch` creates UUIDs (UUIDv4) for all added objects that do not have one at client side (fixes data duplication on Batch retries).
- Adds new methods for :class:`~weaviate.wcs.WCS` for instances that have authentication enabled:
    - :meth:`~weaviate.wcs.WCS.get_users_of_cluster` to get users (emails) for all the users that have access to the created Weaviate instance.
    - :meth:`~weaviate.wcs.WCS.add_user_to_cluster` to add users (email) to the created Weaviate instance.
    - :meth:`~weaviate.wcs.WCS.remove_user_from_cluster` to remove user (email) from the created Weaviate instance.

Version 3.6.0
-------------
This minor version includes:

- New function in :func:`~weaviate.util.check_batch_result` used to print errors from batch creation.

- New function argument ``class_name`` for :func:`~weaviate.util.generate_local_beacon`, used ONLY with Weaviate Server version >= ``1.14.0``
    (defaults to ``None`` for backwards compatibility).

- | :func:`~weaviate.util.check_batch_result` is the default ``callback`` function for :class:`~weaviate.batch.Batch`
    (:meth:`~weaviate.batch.Batch.configure` and :meth:`~weaviate.batch.Batch.__call__`) (instead of ``None``).

- | New method argument ``to_object_class_name``  for :meth:`~weaviate.batch.Batch.add_reference`, used ONLY with Weaviate Server version >= ``1.14.0``
    (defaults to ``None`` for backwards compatibility).

- Support for ``distance`` in GraphQL filters (only with Weaviate server >= ``1.14.0``).

- For :class:`~weaviate.data.DataObject`:
    - | New method argument ``class_name`` for :meth:`~weaviate.data.DataObject.get_by_id`, :meth:`~weaviate.data.DataObject.get`, :meth:`~weaviate.data.DataObject.delete`
        :meth:`~weaviate.data.DataObject.exists`, used ONLY with Weaviate Server version >= ``1.14.0`` (defaults to ``None`` for backwards compatibility).
    - Deprecation Warning if Weaviate Server version >= 1.14.0 and ``class_name`` is ``None`` OR if Weaviate Server version < 1.14.0 and ``class_name`` is NOT ``None``.

- For :class:`~weaviate.data.references.Reference`:
    - | New method arguments ``from_class_name`` and ``to_class_name`` (``to_class_names`` for :meth:`~weaviate.data.references.Reference.update`) for
        :meth:`~weaviate.data.references.Reference.add`, :meth:`~weaviate.data.references.Reference.delete`,
        :meth:`~weaviate.data.references.Reference.update`, used ONLY with Weaviate Server version >= ``1.14.0`` (defaults to ``None`` for backwards compatibility).
    - Deprecation Warning if Weaviate Server version >= 1.14.0 and ``class_name`` is ``None`` OR if Weaviate Server version < 1.14.0 and ``class_name`` is NOT ``None``.


Version 3.5.1
-------------
This patch version fixes:

- | the `rerank` not being set bug in :meth:`~weaviate.gql.get.GetBuilder.with_ask`.

- | the bug when using double quotes(`"`) in `question` field in :meth:`~weaviate.gql.get.GetBuilder.with_ask`.

- | the bug where `nearText` filter checks for objects in `moveXXX` clause but never sets it.


Version 3.5.0
-------------
This minor version contains functionality for the new features introduced in Weaviate ``v1.13.0``.

- | New :class:`~weaviate.batch.Batch` method :meth:`~weaviate.batch.Batch.delete_objects` to delete all objects that match a particular expression (``where`` filter).

- | New :class:`~weaviate.gql.get.GetBuilder` method :meth:`~weaviate.gql.get.GetBuilder.with_sort` that allows sorting data on a particular field/s.

- | New :class:`~weaviate.gql.aggregate.AggregateBuilder` method :meth:`~weaviate.gql.aggregate.AggregateBuilder.with_near_text` that allows to
    aggregate data that is matching ``nearText`` filter.

- | New :class:`~weaviate.gql.aggregate.AggregateBuilder` method :meth:`~weaviate.gql.aggregate.AggregateBuilder.with_near_object` that allows to
    aggregate data that is matching ``nearObject`` filter.

- | New :class:`~weaviate.gql.aggregate.AggregateBuilder` method :meth:`~weaviate.gql.aggregate.AggregateBuilder.with_near_vector` that allows to
    aggregate data that is matching ``nearVector`` filter.

Version 3.4.2
-------------
| This patch version fixes another bug in :meth:`~weaviate.data.DataObject.exists`.

Version 3.4.1
-------------
| This patch version fixes bug in :meth:`~weaviate.data.DataObject.exists`.

Version 3.4.0
-------------
| This minor version fixes the bug in setting the Schema's ``invertedIndexConfig`` field.

| New method :meth:`~weaviate.schema.Schema.get_class_shards` to get all shards configuration of a particular class.

| New method :meth:`~weaviate.schema.Schema.update_class_shard` to update one/all shard/s configuration of a particular class.

| Support for new Property field: ``tokenization``.

Version 3.3.3
-------------
| This patch version fixes the nearImage filter requests.

Version 3.3.2
-------------
| This patch version allows using UUIDs in hex format for :class:`~weaviate.data.DataObject` too i.e. UUIDs without hyphens.

Version 3.3.1
-------------
| This patch version allows using UUIDs in hex format too i.e. UUIDs without hyphens.

Version 3.3.0
-------------
| This minor version adds a new :meth:`~weaviate.gql.get.GetBuilder.with_offset` for the ``Get`` queries. This method should be used
    with the :meth:`~weaviate.gql.get.GetBuilder.with_limit`. This new feature (introduced in weaviate version ``1.8.0``) allows to
    use pagination functionality with the ``Get`` queries. The ``offset`` represents the start index of the objects to be returned,
    and the number of objects is specified by the :meth:`~weaviate.gql.get.GetBuilder.with_limit` method.

| For example, to list the
    first ten results, set ``limit: 10``. Then, to "display the second page of 10", set ``offset: 10, limit: 10`` and so on. E.g.
    to show the 9th page of 10 results, set ``offset: 80, limit: 10`` to effectively display results 81-90.

Version 3.2.5
-------------
This patch fixes the ``'Batch' object is not callable`` error.

Version 3.2.4
-------------
| All ``class_name`` and cross-refs ``dataType`` are implicitly capitalized. (This functionality is added because if ``class_name`` is not capitalized
    then Weaviate server does it for you, and this was leading to errors where the client and server have different configurations.)

Fixes/updates in :class:`~weaviate.schema.Schema` class:

- | This patch fixes the :meth:`~weaviate.schema.Schema.contains` to accept separate class schemas as argument
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


