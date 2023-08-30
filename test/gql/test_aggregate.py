import unittest
from typing import List, Callable, Tuple
from unittest.mock import patch

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.gql.aggregate import AggregateBuilder


class TestAggregateBuilder(unittest.TestCase):
    def setUp(self):
        self.aggregate = AggregateBuilder("Object", None)

    def test_with_meta_count(self):
        """
        Test the `with_meta_count` method.
        """

        query = self.aggregate.with_meta_count().build()
        self.assertEqual("{Aggregate{Object{meta{count}}}}", query)

    def test_with_fields(self):
        """
        Test the `with_fields` method.
        """

        query = self.aggregate.with_fields("size { mean }").build()
        self.assertEqual("{Aggregate{Object{size { mean }}}}", query)

    def test_with_where(self):
        """
        Test the `with_where` method.
        """

        query = (
            self.aggregate.with_meta_count()
            .with_where({"operator": "Equal", "valueString": "B", "path": ["name"]})
            .build()
        )
        self.assertEqual(
            '{Aggregate{Object(where: {path: ["name"] operator: Equal valueString: "B"} ){meta{count}}}}',
            query,
        )

    def test_group_by_filter(self):
        """
        Test the `with_group_by_filter` method.
        """

        query = (
            self.aggregate.with_group_by_filter(["name"])
            .with_fields("groupedBy { value }")
            .with_fields("name { count }")
            .build()
        )
        self.assertEqual(
            '{Aggregate{Object(groupBy: ["name"]){groupedBy { value }name { count }}}}', query
        )

    def test_with_limit(self):
        """
        Test the `with_limit` method.
        """

        query = (
            self.aggregate.with_meta_count()
            .with_where({"operator": "Equal", "valueString": "B", "path": ["name"]})
            .with_limit(10)
            .build()
        )
        self.assertEqual(
            '{Aggregate{Object(where: {path: ["name"] operator: Equal valueString: "B"} limit: 10){meta{count}}}}',
            query,
        )

    test_near_media_param_list: List[
        Tuple[str, str, str, Callable[[AggregateBuilder, str, str, bool], AggregateBuilder]]
    ] = [
        (
            "audio",
            "test_audio",
            "nearAudio",
            lambda b, k, v, e: b.with_near_audio({k: v, "certainty": 0.55}, encode=e),
        ),
        (
            "video",
            "test_video",
            "nearVideo",
            lambda b, k, v, e: b.with_near_video({k: v, "certainty": 0.55}, encode=e),
        ),
        (
            "depth",
            "test_depth",
            "nearDepth",
            lambda b, k, v, e: b.with_near_depth({k: v, "certainty": 0.55}, encode=e),
        ),
        (
            "thermal",
            "test_thermal",
            "nearThermal",
            lambda b, k, v, e: b.with_near_thermal({k: v, "certainty": 0.55}, encode=e),
        ),
        (
            "imu",
            "test_imu",
            "nearIMU",
            lambda b, k, v, e: b.with_near_imu({k: v, "certainty": 0.55}, encode=e),
        ),
    ]

    def test_near_media(self):
        """
        Test the `with_near_<media>` method.
        """
        for key, value, type_, fn in self.test_near_media_param_list:
            with self.subTest(key=key, value=value):
                with patch(
                    "weaviate.gql.aggregate.file_encoder_b64", side_effect=lambda x: "test_call"
                ) as mocked:
                    # valid calls
                    ## encode False
                    query = fn(
                        AggregateBuilder("Person", None).with_fields("name"), key, value, False
                    ).build()
                    self.assertEqual(
                        f'{{Aggregate{{Person({type_}: {{{key}: "{value}" certainty: 0.55}} ){{name}}}}}}',
                        query,
                    )
                    mocked.assert_not_called()

                    ## encode True
                    query = fn(
                        AggregateBuilder("Person", None).with_fields("name"), key, value, True
                    ).build()
                    self.assertEqual(
                        f'{{Aggregate{{Person({type_}: {{{key}: "test_call" certainty: 0.55}} ){{name}}}}}}',
                        query,
                    )
                    mocked.assert_called()

                    # invalid calls
                    near_error_msg = "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"

                    near_text = {
                        "concepts": "computer",
                        "moveTo": {"concepts": ["science"], "force": 0.5},
                    }
                    with self.assertRaises(AttributeError) as error:
                        fn(
                            AggregateBuilder("Person", None)
                            .with_fields("name")
                            .with_near_text(near_text),
                            key,
                            value,
                            True,
                        )
                    check_error_message(self, error, near_error_msg)

    def test_do(self):
        """
        Test the `do` method.
        """

        # test exceptions
        requests_error_message = "Query was not successful."

        # requests.exceptions.ConnectionError
        mock_obj = mock_connection_func("post", side_effect=RequestsConnectionError("Test"))
        self.aggregate._connection = mock_obj
        with self.assertRaises(RequestsConnectionError) as error:
            self.aggregate.do()
        check_error_message(self, error, requests_error_message)

        # weaviate.UnexpectedStatusCodeException
        mock_obj = mock_connection_func("post", status_code=404)
        self.aggregate._connection = mock_obj
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.aggregate.do()
        check_startswith_error_message(self, error, "Query was not successful")

        filter_name = {"path": ["name"], "operator": "Equal", "valueString": "B"}

        self.aggregate.with_group_by_filter(["name"]).with_fields(
            "groupedBy { value }"
        ).with_fields("name { count }").with_where(filter_name)
        expected_gql_clause = '{Aggregate{Object(where: {path: ["name"] operator: Equal valueString: "B"} groupBy: ["name"]){groupedBy { value }name { count }}}}'

        mock_obj = mock_connection_func("post", status_code=200, return_json={"status": "OK!"})
        self.aggregate._connection = mock_obj
        self.assertEqual(self.aggregate.do(), {"status": "OK!"})
        mock_obj.post.assert_called_with(
            path="/graphql", weaviate_object={"query": expected_gql_clause}
        )

    def test_uncapitalized_class_name(self):
        """
        Test the uncapitalized class_name.
        """

        aggregate = AggregateBuilder("Test", None)
        self.assertEqual(aggregate._class_name, "Test")

        aggregate = AggregateBuilder("test", None)
        self.assertEqual(aggregate._class_name, "Test")
