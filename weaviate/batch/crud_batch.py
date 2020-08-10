import sys

from weaviate import SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_ACTIONS
from weaviate.exceptions import *
from weaviate.connect import REST_METHOD_POST


class Batch:

    def __init__(self, connection):
        self._connection = connection

    def create_things(self, things_batch_request):
        """ Creates multiple things at once in weaviate

        :param things_batch_request: The batch of things that should be added.
        :type things_batch_request: weaviate.ThingsBatchRequest
        :return: A list with the status of every thing that was created.
        :rtype: list
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._create_entity_in_batch(SEMANTIC_TYPE_THINGS, things_batch_request)

    def create_actions(self, actions_batch_request):
        """ Crate multiple actions at once in weavaite

        :param actions_batch_request: The batch of actions that should be added.
        :type actions_batch_request: weaviate.ActionsBatchRequest
        :return: A list with the status of every action that was created
        :rtype: list
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._create_entity_in_batch(SEMANTIC_TYPE_ACTIONS, actions_batch_request)

    def _create_entity_in_batch(self, semantic_type, batch_request):
        path = "/batching/" + semantic_type

        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, batch_request.get_request_body())
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, batch was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()

        else:
            raise UnexpectedStatusCodeException("Create " + semantic_type + " in batch", response)

    def add_references(self, reference_batch_request):
        """ Batch loading references
            Loading batch references is faster by ignoring some validations.
            Loading inconsistent data may ends up in an invalid graph.
            If the consistency of the references is not guaranied use
            add_reference_to_thing to have additional validation instead.

            :param reference_batch_request: contains all the references that should be added in one batch.
            :type reference_batch_request: weaviate.batch.ReferenceBatchRequest
            :return: A list with the status of every reference added.
            :raises:
                ConnectionError: if the network connection to weaviate fails.
                UnexpectedStatusCodeException: if weaviate reports a none OK status.
            """

        if reference_batch_request.get_batch_size() == 0:
            return  # No data in batch

        path = "/batching/references"

        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, reference_batch_request.get_request_body())
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, reference was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Add references in batch", response)


