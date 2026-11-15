Weaviate Exceptions
===================

Generative query errors
-----------------------

Failed searches through ``collection.generate`` raise
``WeaviateGenerativeQueryError``, including timeouts and exhausted retries.
It is a subclass of ``WeaviateQueryError``, so existing query error handlers
continue to catch these failures. Permission failures still raise
``InsufficientPermissionsError``.

Catch the specific exception first to provide troubleshooting guidance for
retrieval-augmented generation. Depending on the underlying error, check the
generative provider configuration, credentials, rate limits, or query timeout.
The original error details are preserved in ``message`` and ``error``; the
exception does not imply that the generation step caused the failure, since
retrieval can also fail.

.. code-block:: python

   from weaviate.exceptions import WeaviateGenerativeQueryError, WeaviateQueryError

   try:
       response = collection.generate.fetch_objects(grouped_task="Summarize these objects")
   except WeaviateGenerativeQueryError as error:
       print(f"Generative query failed: {error.message}")
   except WeaviateQueryError as error:
       print(f"Query failed: {error.message}")

Exception reference
-------------------

.. automodule:: weaviate.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
