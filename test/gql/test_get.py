import unittest
from typing import List, Optional, Callable, Tuple
from unittest.mock import patch, Mock

import pytest

from test.util import check_error_message
from weaviate.data.replication import ConsistencyLevel
from weaviate.gql.get import (
    GetBuilder,
    BM25,
    Hybrid,
    LinkTo,
    GroupBy,
    AdditionalProperties,
    HybridFusion,
)

mock_connection_v117 = Mock()
mock_connection_v117.server_version = "1.17.4"


@pytest.mark.parametrize(
    "props,expected",
    [
        (AdditionalProperties(uuid=True), " _additional{id} "),
        (
            AdditionalProperties(uuid=True, vector=True, explainScore=True),
            " _additional{id vector explainScore} ",
        ),
        (
            AdditionalProperties(uuid=False, vector=True, explainScore=True, score=True),
            " _additional{vector score explainScore} ",
        ),
    ],
)
def test_additional_props(props: AdditionalProperties, expected: str):
    assert str(props) == expected


@pytest.mark.parametrize(
    "additional_props,expected",
    [
        (AdditionalProperties(uuid=True), " _additional{id} "),
    ],
)
def test_getbuilder_with_additional_props(additional_props: AdditionalProperties, expected: str):
    query = (
        GetBuilder("TestClass", "name", mock_connection_v117)
        .with_additional(additional_props)
        .build()
    )
    expected_query = "{Get{TestClass{name" + expected + "}}}"
    assert (
        "name_" not in expected_query
    )  # Check that the prop name is not being concatnated to _additional
    assert query == expected_query


@pytest.mark.parametrize(
    "query,properties,expected",
    [
        (
            "query",
            ["title", "document", "date"],
            'bm25:{query: "query", properties: ["title","document","date"]}',
        ),
        ("other query", [], 'bm25:{query: "other query"}'),
        ("other query", None, 'bm25:{query: "other query"}'),
        ('what is an "airport"', None, 'bm25:{query: "what is an \\"airport\\""}'),
        ("what is an 'airport'", None, """bm25:{query: "what is an 'airport'"}"""),
    ],
)
def test_bm25(query: str, properties: List[str], expected: str):
    bm25 = BM25(query, properties)
    assert str(bm25) == expected


@pytest.mark.parametrize(
    "property_name,in_class,properties,expected",
    [
        (
            "property",
            "class",
            ["title"],
            "property{... on class{title}}",
        ),
        (
            "property",
            "class",
            ["title", "document", "date"],
            "property{... on class{title document date}}",
        ),
    ],
)
def test_get_references(property_name: str, in_class: str, properties: List[str], expected: str):
    ref = LinkTo(property_name, in_class, properties)
    assert str(ref) == expected


@pytest.mark.parametrize(
    "query,vector,alpha,properties,fusion_type,expected",
    [
        (
            "query",
            [1, 2, 3],
            0.5,
            None,
            None,
            'hybrid:{query: "query", vector: [1, 2, 3], alpha: 0.5}',
        ),
        ("query", None, None, None, None, 'hybrid:{query: "query"}'),
        ('query "query2"', None, None, None, None, 'hybrid:{query: "query \\"query2\\""}'),
        ("query 'query2'", None, None, None, None, """hybrid:{query: "query 'query2'"}"""),
        ("query", None, None, ["prop1"], None, 'hybrid:{query: "query", properties: ["prop1"]}'),
        (
            "query",
            None,
            None,
            ["prop1", "prop2"],
            None,
            'hybrid:{query: "query", properties: ["prop1","prop2"]}',
        ),
        (
            "query",
            None,
            None,
            None,
            HybridFusion.RANKED,
            'hybrid:{query: "query", fusionType: rankedFusion}',
        ),
        (
            "query",
            None,
            None,
            None,
            HybridFusion.RELATIVE_SCORE,
            'hybrid:{query: "query", fusionType: relativeScoreFusion}',
        ),
        (
            "query",
            None,
            None,
            None,
            "relativeScoreFusion",
            'hybrid:{query: "query", fusionType: relativeScoreFusion}',
        ),
    ],
)
def test_hybrid(
    query: str,
    vector: Optional[List[float]],
    alpha: Optional[float],
    properties: Optional[List[str]],
    fusion_type: HybridFusion,
    expected: str,
):
    hybrid = Hybrid(query, alpha, vector, properties, fusion_type)
    assert str(hybrid) == expected


@pytest.mark.parametrize(
    "single_prompt,grouped_task,grouped_properties,expected",
    [
        (
            "What is the meaning of life?",
            None,
            None,
            """generate(singleResult:{prompt:"What is the meaning of life?"}){error singleResult} """,
        ),
        (
            'What is the meaning of "life"?',
            None,
            None,
            """generate(singleResult:{prompt:"What is the meaning of \\"life\\"?"}){error singleResult} """,
        ),
        (
            "What is the meaning of 'life'?",
            None,
            None,
            """generate(singleResult:{prompt:"What is the meaning of 'life'?"}){error singleResult} """,
        ),
        (
            None,
            "Explain why these magazines or newspapers are about finance",
            None,
            """generate(groupedResult:{task:"Explain why these magazines or newspapers are about finance"}){error groupedResult} """,
        ),
        (
            None,
            'Explain why these magazines or newspapers are about "finance"',
            None,
            """generate(groupedResult:{task:"Explain why these magazines or newspapers are about \\"finance\\""}){error groupedResult} """,
        ),
        (
            None,
            "Explain why these magazines or newspapers are about 'finance'",
            None,
            """generate(groupedResult:{task:"Explain why these magazines or newspapers are about 'finance'"}){error groupedResult} """,
        ),
        (
            "What is the meaning of life?",
            "Explain why these magazines or newspapers are about finance",
            None,
            """generate(singleResult:{prompt:"What is the meaning of life?"}groupedResult:{task:"Explain why these magazines or newspapers are about finance"}){error singleResult groupedResult} """,
        ),
        (
            None,
            "Explain why these magazines or newspapers are about finance",
            ["description"],
            """generate(groupedResult:{task:"Explain why these magazines or newspapers are about finance",properties:["description"]}){error groupedResult} """,
        ),
        (
            "What is the meaning of life?",
            "Explain why these magazines or newspapers are about finance",
            ["title", "description"],
            """generate(singleResult:{prompt:"What is the meaning of life?"}groupedResult:{task:"Explain why these magazines or newspapers are about finance",properties:["title","description"]}){error singleResult groupedResult} """,
        ),
    ],
)
def test_generative(
    single_prompt: str, grouped_task: str, grouped_properties: List[str], expected: str
):
    query = (
        GetBuilder("Person", "name", mock_connection_v117)
        .with_generate(single_prompt, grouped_task, grouped_properties)
        .build()
    )
    expected_query = "{Get{Person{name _additional {" + expected + "}}}}"
    assert query == expected_query


@pytest.mark.parametrize("single_prompt,grouped_task", [(123, None), (None, None), (None, 123)])
def test_generative_type(single_prompt: str, grouped_task: str):
    with pytest.raises(TypeError):
        GetBuilder("Person", "name", mock_connection_v117).with_generate(
            single_prompt, grouped_task
        ).build()


@pytest.mark.parametrize(
    "properties,groups,max_groups,expected",
    [
        (
            ["prop1", "prop2"],
            2,
            3,
            'groupBy:{path:["prop1","prop2"], groups:2, objectsPerGroup:3}',
        ),
        (
            ["prop1"],
            4,
            5,
            'groupBy:{path:["prop1"], groups:4, objectsPerGroup:5}',
        ),
    ],
)
def test_groupy(properties: List[str], groups: int, max_groups: int, expected: str):
    assert str(GroupBy(properties, groups, max_groups)) == expected


class TestGetBuilder(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        class_name_error_msg = f"class name must be of type str but was {int}"
        properties_error_msg = (
            "properties must be of type str, " f"list of str or None but was {int}"
        )
        property_error_msg = "All the `properties` must be of type `str` or Reference!"

        # invalid calls
        with self.assertRaises(TypeError) as error:
            GetBuilder(1, ["a"], None)
        check_error_message(self, error, class_name_error_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("A", 2, None)
        check_error_message(self, error, properties_error_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("A", [True], None)
        check_error_message(self, error, property_error_msg)

        # valid calls
        GetBuilder("name", "prop", None)
        GetBuilder("name", ["prop1", "prop2"], None)

    def test_build_with_limit(self):
        """
        Test the `with_limit` method.
        """

        # valid calls
        query = GetBuilder("Person", "name", None).with_limit(20).build()
        self.assertEqual("{Get{Person(limit: 20 ){name}}}", query)

        # invalid calls
        limit_error_msg = "limit cannot be non-positive (limit >=1)."
        with self.assertRaises(ValueError) as error:
            GetBuilder("A", ["str"], None).with_limit(0)
        check_error_message(self, error, limit_error_msg)

        with self.assertRaises(ValueError) as error:
            GetBuilder("A", ["str"], None).with_limit(-1)
        check_error_message(self, error, limit_error_msg)

    def test_build_with_offset(self):
        """
        Test the `with_limit` method.
        """

        # valid calls
        query = GetBuilder("Person", "name", None).with_offset(20).build()
        self.assertEqual("{Get{Person(offset: 20 ){name}}}", query)

        query = GetBuilder("Person", "name", None).with_offset(0).build()
        self.assertEqual("{Get{Person(offset: 0 ){name}}}", query)

        # invalid calls
        limit_error_msg = "offset cannot be non-positive (offset >=0)."
        with self.assertRaises(ValueError) as error:
            GetBuilder("A", ["str"], None).with_offset(-1)
        check_error_message(self, error, limit_error_msg)

    def test_build_with_consistency_level(self):
        """
        Test the `with_consistency_level` method
        """

        query = (
            GetBuilder("Person", "name", None).with_consistency_level(ConsistencyLevel.ONE).build()
        )
        self.assertEqual("{Get{Person(consistencyLevel: ONE ){name}}}", query)

        query = (
            GetBuilder("Person", "name", None)
            .with_consistency_level(ConsistencyLevel.QUORUM)
            .build()
        )
        self.assertEqual("{Get{Person(consistencyLevel: QUORUM ){name}}}", query)

        query = (
            GetBuilder("Person", "name", None).with_consistency_level(ConsistencyLevel.ALL).build()
        )
        self.assertEqual("{Get{Person(consistencyLevel: ALL ){name}}}", query)

    def test_build_with_where(self):
        """
        Test the ` with_where` method.
        """

        filter_name = {"path": ["name"], "operator": "Equal", "valueString": "A"}
        query = GetBuilder("Person", "name", None).with_where(filter_name).build()
        self.assertEqual(
            '{Get{Person(where: {path: ["name"] operator: Equal valueString: "A"} ){name}}}', query
        )

    def test_build_with_near_text(self):
        """
        Test the `with_near_text` method.
        """

        near_text = {
            "concepts": "computer",
            "moveTo": {"concepts": ["science"], "force": 0.5},
            "autocorrect": True,
        }

        # valid calls
        query = GetBuilder("Person", "name", None).with_near_text(near_text).build()
        self.assertEqual(
            '{Get{Person(nearText: {concepts: ["computer"] moveTo: {force: 0.5 concepts: ["science"]} autocorrect: true} ){name}}}',
            query,
        )

        # invalid calls
        near_error_msg = (
            "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"
        )

        near_vector = {"vector": [1, 2, 3, 4, 5, 6, 7, 8, 9], "certainty": 0.55}
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", None).with_near_vector(near_vector).with_near_text(
                near_text
            )
        check_error_message(self, error, near_error_msg)

    def test_build_near_vector(self):
        """
        Test the `with_near_vector` method.
        """

        near_vector = {"vector": [1, 2, 3, 4, 5, 6, 7, 8, 9], "certainty": 0.55}

        # valid calls
        mock_connection = Mock()
        mock_connection.server_version = "1.14.0"
        query = GetBuilder("Person", "name", mock_connection).with_near_vector(near_vector).build()
        self.assertEqual(
            "{Get{Person(nearVector: {vector: [1, 2, 3, 4, 5, 6, 7, 8, 9] certainty: 0.55} ){name}}}",
            query,
        )

        # invalid calls
        near_error_msg = (
            "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"
        )

        near_object = {"id": "test_id", "certainty": 0.55}
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", mock_connection).with_near_object(
                near_object
            ).with_near_vector(near_vector)
        check_error_message(self, error, near_error_msg)

    def test_build_near_object(self):
        """
        Test the `with_near_object` method.
        """

        near_object = {"id": "test_id", "certainty": 0.55}

        # valid calls
        mock_connection = Mock()
        mock_connection.server_version = "1.14.0"
        query = GetBuilder("Person", "name", mock_connection).with_near_object(near_object).build()
        self.assertEqual('{Get{Person(nearObject: {id: "test_id" certainty: 0.55} ){name}}}', query)

        # invalid calls
        near_error_msg = (
            "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"
        )

        near_text = {
            "concepts": "computer",
            "moveTo": {"concepts": ["science"], "force": 0.5},
        }
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", mock_connection).with_near_text(
                near_text
            ).with_near_object(near_object)
        check_error_message(self, error, near_error_msg)

    @patch("weaviate.gql.get.image_encoder_b64", side_effect=lambda x: "test_call")
    def test_build_near_image(self, mock_image_encoder_b64: Mock):
        """
        Test the `with_near_object` method.
        """

        near_image = {"image": "test_image", "certainty": 0.55}

        # valid calls
        ## encode False
        query = GetBuilder("Person", "name", None).with_near_image(near_image, encode=False).build()
        self.assertEqual(
            '{Get{Person(nearImage: {image: "test_image" certainty: 0.55} ){name}}}', query
        )
        mock_image_encoder_b64.assert_not_called()

        ## encode True
        query = GetBuilder("Person", "name", None).with_near_image(near_image, encode=True).build()
        self.assertEqual(
            '{Get{Person(nearImage: {image: "test_call" certainty: 0.55} ){name}}}', query
        )
        mock_image_encoder_b64.assert_called()

        # invalid calls
        near_error_msg = (
            "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"
        )

        near_text = {
            "concepts": "computer",
            "moveTo": {"concepts": ["science"], "force": 0.5},
        }
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", None).with_near_text(near_text).with_near_image(near_image)
        check_error_message(self, error, near_error_msg)

    test_build_near_media_param_list: List[
        Tuple[str, str, str, Callable[[GetBuilder, str, str, bool], GetBuilder]]
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

    def test_build_near_media(self):
        """
        Test the `with_near_<media>` method.
        """
        for key, value, type_, fn in self.test_build_near_media_param_list:
            with self.subTest(key=key, value=value):
                with patch(
                    "weaviate.gql.get.file_encoder_b64", side_effect=lambda x: "test_call"
                ) as mocked:
                    # valid calls
                    ## encode False
                    query = fn(GetBuilder("Person", "name", None), key, value, False).build()
                    self.assertEqual(
                        f'{{Get{{Person({type_}: {{{key}: "{value}" certainty: 0.55}} ){{name}}}}}}',
                        query,
                    )
                    mocked.assert_not_called()

                    ## encode True
                    query = fn(GetBuilder("Person", "name", None), key, value, True).build()
                    self.assertEqual(
                        f'{{Get{{Person({type_}: {{{key}: "test_call" certainty: 0.55}} ){{name}}}}}}',
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
                            GetBuilder("Person", "name", None).with_near_text(near_text),
                            key,
                            value,
                            True,
                        )
                    check_error_message(self, error, near_error_msg)

    def test_build_ask(self):
        """
        Test the `with_ask` method.
        """

        ask = {
            "question": "What is k8s?",
            "certainty": 0.55,
            "autocorrect": False,
        }

        # valid calls
        query = GetBuilder("Person", "name", None).with_ask(ask).build()
        self.assertEqual(
            '{Get{Person(ask: {question: "What is k8s?" certainty: 0.55 autocorrect: false} ){name}}}',
            query,
        )

        # invalid calls
        near_error_msg = (
            "Cannot use multiple 'near' filters, or a 'near' filter along with a 'ask' filter!"
        )

        near_text = {
            "concepts": "computer",
            "moveTo": {"concepts": ["science"], "force": 0.5},
        }
        with self.assertRaises(AttributeError) as error:
            GetBuilder("Person", "name", None).with_near_text(near_text).with_ask(ask)
        check_error_message(self, error, near_error_msg)

    def test_build_with_additional(self):
        """
        Test the `with_additional` method.
        """

        # valid calls
        ## `str` as argument
        query = GetBuilder("Person", "name", None).with_additional("id").build()
        self.assertEqual("{Get{Person{name _additional {id }}}}", query)

        ## list of `str` as argument
        query = (
            GetBuilder("Person", "name", None).with_additional(["id", "certainty", "test"]).build()
        )
        self.assertEqual("{Get{Person{name _additional {certainty id test }}}}", query)

        ## dict with value `str` as argument
        query = GetBuilder("Person", "name", None).with_additional({"classification": "id"}).build()
        self.assertEqual("{Get{Person{name _additional {classification {id } }}}}", query)

        ## dict with value list of `str` as argument
        query = (
            GetBuilder("Person", "name", None)
            .with_additional({"classification": ["basedOn", "classifiedFields", "completed", "id"]})
            .build()
        )
        self.assertEqual(
            "{Get{Person{name _additional {classification {basedOn classifiedFields completed id } }}}}",
            query,
        )

        ## dict with value list of `tuple` as argument
        clause = {"token": ["entity", "word"]}
        settings = {"test1": 1, "test3": [True], "test2": 10.0}
        query = GetBuilder("Person", "name", None).with_additional((clause, settings)).build()
        self.assertEqual(
            "{Get{Person{name _additional {token(test1: 1 test2: 10.0 test3: [true] ) {entity word } }}}}",
            query,
        )

        ## dict with value list of `tuple` as argument
        clause = {"token": "certainty"}
        settings = {"test1": ["TEST"]}
        query = GetBuilder("Person", "name", None).with_additional((clause, settings)).build()
        self.assertEqual(
            '{Get{Person{name _additional {token(test1: ["TEST"] ) {certainty } }}}}', query
        )

        ## multiple calls
        clause = {"token": "certainty"}
        settings = {"test1": ["TEST"]}
        query = (
            GetBuilder("Person", "name", None)
            .with_additional("test")
            .with_additional(["id", "certainty"])
            .with_additional({"classification": ["completed", "id"]})
            .with_additional((clause, settings))
            .build()
        )
        self.assertEqual(
            '{Get{Person{name _additional {certainty id test classification {completed id } token(test1: ["TEST"] ) {certainty } }}}}',
            query,
        )

        ## multiple calls
        query = (
            GetBuilder("Person", None, None)
            .with_additional("test")
            .with_additional(["id", "certainty"])
            .with_additional({"classification": ["completed", "id"]})
            .with_additional("id")
            .with_additional("test")
            .build()
        )
        self.assertEqual(
            "{Get{Person{ _additional {certainty id test classification {completed id } }}}}", query
        )

        # invalid calls
        # error messages
        prop_type_msg = lambda dt: (
            "The 'properties' argument must be either of type `str`, `list`, `dict` or `tuple`! "
            f"Given: {dt}"
        )
        prop_list_msg = "If type of 'properties' is `list` then all items must be of type `str`!"
        prop_dict_key_msg = "If type of 'properties' is `dict` then all keys must be of type `str`!"
        prop_dict_value_msg = lambda dt: (
            "If type of 'properties' is `dict` then all the values must be either of type "
            f"`str` or `list` of `str`! Given: {dt}!"
        )
        prop_dict_value_len = (
            "If type of 'properties' is `dict` and a value is of type `list` then at least"
            " one element should be present!"
        )
        prop_dict_value_item_msg = (
            "If type of 'properties' is `dict` and a value is of type `list` then all "
            "items must be of type `str`!"
        )
        prop_tuple_len_msg = (
            "If type of 'properties' is `tuple` then it should have length 2: "
            "(clause: <dict>, settings: <dict>)"
        )
        prop_tuple_type_msg = (
            "If type of 'properties' is `tuple` then it should have this data type: "
            "(<dict>, <dict>)"
        )
        prop_tuple_clause_len_msg = lambda clause: (
            "If type of 'properties' is `tuple` then the 'clause' (first element) should "
            f"have only one key. Given: {len(clause)}"
        )
        prop_tuple_settings_len_msg = lambda settings: (
            "If type of 'properties' is `tuple` then the 'settings' (second element) should "
            f"have at least one key. Given: {len(settings)}"
        )
        prop_tuple_clause_key_type_msg = (
            "If type of 'properties' is `tuple` then first element's key should be of type "
            "`str`!"
        )
        prop_tuple_settings_keys_type_msg = (
            "If type of 'properties' is `tuple` then the second elements (<dict>) should "
            "have all the keys of type `str`!"
        )
        prop_tuple_clause_value_type_msg = lambda dt: (
            "If type of 'properties' is `tuple` then first element's dict values must be "
            f"either of type `str` or `list` of `str`! Given: {dt}!"
        )
        prop_tuple_clause_value_len_msg = (
            "If type of 'properties' is `tuple` and first element's dict value is of type "
            "`list` then at least one element should be present!"
        )
        prop_tuple_clause_values_items_type_msg = (
            "If type of 'properties' is `tuple` and first element's dict value is of type "
            " `list` then all items must be of type `str`!"
        )

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional(123)
        check_error_message(self, error, prop_type_msg(int))

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional([123])
        check_error_message(self, error, prop_list_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional({123: "Test"})
        check_error_message(self, error, prop_dict_key_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional({"test": True})
        check_error_message(self, error, prop_dict_value_msg(bool))

        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional({"test": []})
        check_error_message(self, error, prop_dict_value_len)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional({"test": [True]})
        check_error_message(self, error, prop_dict_value_item_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional({"test": [True]})
        check_error_message(self, error, prop_dict_value_item_msg)

        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional((1,))
        check_error_message(self, error, prop_tuple_len_msg)

        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional((1, 2, 3))
        check_error_message(self, error, prop_tuple_len_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional(({1: "1"}, ["test"]))
        check_error_message(self, error, prop_tuple_type_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional(([{1: "1"}], ["test"]))
        check_error_message(self, error, prop_tuple_type_msg)

        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((["test"], {1: "1"}))
        check_error_message(self, error, prop_tuple_type_msg)

        clause = {"test1": 1, "test2": 2}
        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, {"1": "1"}))
        check_error_message(self, error, prop_tuple_clause_len_msg(clause))

        clause = {"test1": "1"}
        settings = {}
        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_settings_len_msg(settings))

        clause = {1: "1"}
        settings = {"test": 1}
        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_clause_key_type_msg)

        clause = {"test": "1"}
        settings = {"test": 1, 2: 2}
        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_settings_keys_type_msg)

        clause = {"test": "1"}
        settings = {2: 2}
        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_settings_keys_type_msg)

        clause = {"test": True}
        settings = {"test": 2}
        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_clause_value_type_msg(bool))

        clause = {"test": []}
        settings = {"test": 2}
        with self.assertRaises(ValueError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_clause_value_len_msg)

        clause = {"test": ["1", "2", 3]}
        settings = {"test": 2}
        with self.assertRaises(TypeError) as error:
            GetBuilder("Person", "name", None).with_additional((clause, settings))
        check_error_message(self, error, prop_tuple_clause_values_items_type_msg)

    def test_build(self):
        """
        Test the `build` method. (without filters)
        """

        error_message = (
            "No 'properties' or 'additional properties' specified to be returned. "
            "At least one should be included."
        )

        with self.assertRaises(AttributeError) as error:
            query = GetBuilder("Group", [], None).build()
        check_error_message(self, error, error_message)

        query = GetBuilder("Group", "name", None).build()
        self.assertEqual("{Get{Group{name}}}", query)

        query = GetBuilder("Group", ["name", "uuid"], None).build()
        self.assertEqual("{Get{Group{name uuid}}}", query)

        query = GetBuilder("Group", None, None).with_additional("distance").build()
        self.assertEqual("{Get{Group{ _additional {distance }}}}", query)

        near_text = {
            "concepts": ["computer"],
            "moveTo": {"concepts": "science", "force": 0.1},
            "moveAwayFrom": {"concepts": ["airplane"], "force": 0.2},
            "certainty": 0.3,
        }
        or_filter = {
            "operator": "Or",
            "operands": [
                {
                    "path": ["name"],
                    "operator": "Equal",
                    "valueString": "Alan Turing",
                },
                {"path": ["name"], "operator": "Equal", "valueString": "John von Neumann"},
            ],
        }
        query = (
            GetBuilder("Person", ["name", "uuid"], None)
            .with_near_text(near_text)
            .with_where(or_filter)
            .with_limit(2)
            .with_offset(10)
            .build()
        )
        self.assertEqual(
            '{Get{Person(where: {operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Turing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]} limit: 2 offset: 10 nearText: {concepts: ["computer"] certainty: 0.3 moveTo: {force: 0.1 concepts: ["science"]} moveAwayFrom: {force: 0.2 concepts: ["airplane"]}} ){name uuid}}}',
            query,
        )

    def test_capitalized_class_name(self):
        """
        Test the capitalized class_name.
        """

        get = GetBuilder("Test", ["prop"], None)
        self.assertEqual(get._class_name, "Test")

        get = GetBuilder("test", ["prop"], None)
        self.assertEqual(get._class_name, "Test")
