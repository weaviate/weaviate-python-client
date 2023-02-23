import unittest

from test.util import check_error_message, check_startswith_error_message
from weaviate.gql.filter import NearText, NearVector, NearObject, NearImage, Where, Ask


def helper_get_test_filter(filter_type, value):
    return {"path": ["name"], "operator": "Equal", filter_type: value}


class TestNearText(unittest.TestCase):
    def move_x_test_case(self, move: str):
        """
        Test the "moveTo" or the "moveAwayFrom" clause.

        Parameters
        ----------
        move : str
            The "moveTo" or the "moveAwayFrom" clause name.
        """

        type_error_msg = (
            lambda dt: f"'moveXXX' key-value is expected to be of type <class 'dict'> but is {dt}!"
        )
        concepts_objects_error_msg = "The 'move' clause should contain `concepts` OR/AND `objects`!"
        objects_type_error_msg = (
            lambda dt: f"'objects' key-value is expected to be of type (<class 'list'>, <class 'dict'>) but is {dt}!"
        )
        object_value_error_msg = (
            "Each object from the `move` clause should have ONLY `id` OR `beacon`!"
        )
        concept_value_error_msg = lambda dt: (
            f"'concepts' key-value is expected to be of type (<class 'list'>, <class 'str'>) but is {dt}!"
        )
        force_error_msg = "'move' clause needs to state a 'force'"
        force_type_error_msg = lambda dt: (
            f"'force' key-value is expected to be of type <class 'float'> but is {dt}!"
        )

        with self.assertRaises(TypeError) as error:
            NearText({"concepts": "Some_concept", move: "0.5"})
        check_error_message(self, error, type_error_msg(str))

        with self.assertRaises(ValueError) as error:
            NearText({"concepts": "Some_concept", move: {}})
        check_error_message(self, error, concepts_objects_error_msg)

        with self.assertRaises(TypeError) as error:
            NearText({"concepts": "Some_concept", move: {"concepts": set("something")}})
        check_error_message(self, error, concept_value_error_msg(set))

        with self.assertRaises(ValueError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {
                        "concepts": "something",
                    },
                }
            )
        check_error_message(self, error, force_error_msg)

        with self.assertRaises(TypeError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {
                        "objects": 1234,
                    },
                }
            )
        check_error_message(self, error, objects_type_error_msg(int))

        with self.assertRaises(ValueError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {
                        "objects": {},
                    },
                }
            )
        check_error_message(self, error, object_value_error_msg)

        with self.assertRaises(ValueError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {
                        "objects": {"id": 1, "beacon": 2},
                    },
                }
            )
        check_error_message(self, error, object_value_error_msg)

        with self.assertRaises(ValueError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {
                        "objects": {"test_id": 1},
                    },
                }
            )
        check_error_message(self, error, object_value_error_msg)

        with self.assertRaises(TypeError) as error:
            NearText(
                {
                    "concepts": "Some_concept",
                    move: {"concepts": "something", "objects": [{"id": 1}], "force": True},
                }
            )
        check_error_message(self, error, force_type_error_msg(bool))

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # invalid calls
        content_error_msg = f"NearText filter is expected to be type dict but is {list}"
        concept_error_msg = "No concepts in content"
        concept_value_error_msg = lambda actual_type: (
            f"'concepts' key-value is expected to be of type (<class 'list'>, <class 'str'>) but is {actual_type}!"
        )
        certainty_error_msg = lambda dtype: (
            f"'certainty' key-value is expected to be of type <class 'float'> but is {dtype}!"
        )
        autocorrect_error_msg = lambda dtype: (
            f"'autocorrect' key-value is expected to be of type <class 'bool'> but is {dtype}!"
        )

        ## test "concepts"
        with self.assertRaises(TypeError) as error:
            NearText(["concepts", "Some_concept"])
        check_error_message(self, error, content_error_msg)

        with self.assertRaises(ValueError) as error:
            NearText({"INVALID": "Some_concept"})
        check_error_message(self, error, concept_error_msg)

        with self.assertRaises(TypeError) as error:
            NearText({"concepts": set("Some_concept")})
        check_error_message(self, error, concept_value_error_msg(set))

        ## test "certainty"
        with self.assertRaises(TypeError) as error:
            NearText({"concepts": "Some_concept", "certainty": "0.5"})
        check_error_message(self, error, certainty_error_msg(str))

        ## test "certainty"
        with self.assertRaises(TypeError) as error:
            NearText({"concepts": "Some_concept", "autocorrect": [True]})
        check_error_message(self, error, autocorrect_error_msg(list))

        ## test "moveTo"
        self.move_x_test_case("moveTo")
        ## test "moveAwayFrom"
        self.move_x_test_case("moveAwayFrom")

        # test valid calls
        NearText({"concepts": "Some_concept"})
        NearText({"concepts": ["Some_concept", "Some_concept_2"]})
        NearText({"concepts": "Some_concept", "certainty": 0.75})
        NearText({"concepts": "Some_concept", "certainty": 0.75, "autocorrect": True})
        NearText(
            {"concepts": "Some_concept", "moveTo": {"concepts": "moveToConcepts", "force": 0.75}}
        )
        NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {"concepts": "moveAwayFromConcepts", "force": 0.75},
            }
        )
        NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.75,
                "moveAwayFrom": {"concepts": "moveAwayFromConcepts", "force": 0.75},
                "moveTo": {"concepts": "moveToConcepts", "force": 0.75},
                "autocorrect": False,
            }
        )

        NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.75,
                "moveAwayFrom": {"objects": {"id": "test_id"}, "force": 0.75},
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "objects": [{"id": "test_id"}, {"beacon": "Test_beacon"}],
                    "force": 0.75,
                },
                "autocorrect": True,
            }
        )

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        near_text = NearText({"concepts": "Some_concept"})
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"]} ')

        near_text = NearText({"concepts": ["Some_concept", "Some_concept_2"]})
        self.assertEqual(
            str(near_text), 'nearText: {concepts: ["Some_concept", "Some_concept_2"]} '
        )
        near_text = NearText({"concepts": "Some_concept", "certainty": 0.75})
        self.assertEqual(str(near_text), 'nearText: {concepts: ["Some_concept"] certainty: 0.75} ')
        near_text = NearText({"concepts": "Some_concept", "autocorrect": True})
        self.assertEqual(
            str(near_text), 'nearText: {concepts: ["Some_concept"] autocorrect: true} '
        )
        near_text = NearText({"concepts": "Some_concept", "autocorrect": False})
        self.assertEqual(
            str(near_text), 'nearText: {concepts: ["Some_concept"] autocorrect: false} '
        )
        near_text = NearText(
            {"concepts": "Some_concept", "moveTo": {"concepts": "moveToConcepts", "force": 0.75}}
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveTo: {force: 0.75 concepts: ["moveToConcepts"]}} ',
        )
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveTo": {
                    "concepts": "moveToConcepts",
                    "force": 0.75,
                    "objects": {"id": "SOME_ID"},
                },
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveTo: {force: 0.75 concepts: ["moveToConcepts"] objects: [{id: "SOME_ID"} ]}} ',
        )

        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveTo": {
                    "force": 0.75,
                    "objects": [{"id": "SOME_ID"}, {"beacon": "SOME_BEACON"}],
                },
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveTo: {force: 0.75 objects: [{id: "SOME_ID"} {beacon: "SOME_BEACON"} ]}} ',
        )

        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {
                    "concepts": "moveAwayFromConcepts",
                    "force": 0.75,
                    "objects": {"id": "SOME_ID"},
                },
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveAwayFrom: {force: 0.75 concepts: ["moveAwayFromConcepts"] objects: [{id: "SOME_ID"} ]}} ',
        )

        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {
                    "force": 0.75,
                    "objects": [{"id": "SOME_ID"}, {"beacon": "SOME_BEACON"}],
                },
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveAwayFrom: {force: 0.75 objects: [{id: "SOME_ID"} {beacon: "SOME_BEACON"} ]}} ',
        )

        near_text = NearText(
            {
                "concepts": "Some_concept",
                "moveAwayFrom": {"concepts": "moveAwayFromConcepts", "force": 0.25},
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] moveAwayFrom: {force: 0.25 concepts: ["moveAwayFromConcepts"]}} ',
        )
        near_text = NearText(
            {
                "concepts": "Some_concept",
                "certainty": 0.95,
                "moveAwayFrom": {"concepts": "moveAwayFromConcepts", "force": 0.75},
                "moveTo": {"concepts": "moveToConcepts", "force": 0.25},
                "autocorrect": True,
            }
        )
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["Some_concept"] certainty: 0.95 moveTo: {force: 0.25 concepts: ["moveToConcepts"]} moveAwayFrom: {force: 0.75 concepts: ["moveAwayFromConcepts"]} autocorrect: true} ',
        )

        # test it with references of objects
        concepts = ["con1", "con2"]
        move = {"concepts": "moveToConcepts", "force": 0.75}

        near_text = NearText({"concepts": concepts, "moveTo": move})
        concepts.append("con3")  # should not be appended to the nearText clause
        move["force"] = 2.00  # should not be appended to the nearText clause
        self.assertEqual(
            str(near_text),
            'nearText: {concepts: ["con1", "con2"] moveTo: {force: 0.75 concepts: ["moveToConcepts"]}} ',
        )


class TestNearVector(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        content_error_msg = "NearVector filter is expected to " f"be type dict but is {list}"
        vector_error_msg = "\"No 'vector' key in `content` argument.\""
        vector_value_error_msg = (
            "The type of the 'vector' argument is not supported!\n"
            "Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` "
            "and `tf.Tensor`"
        )
        certainty_error_msg = lambda dtype: (
            f"'certainty' key-value is expected to be of type <class 'float'> but is {dtype}!"
        )

        ## test "concepts"
        with self.assertRaises(TypeError) as error:
            NearVector(["concepts", "Some_concept"])
        check_error_message(self, error, content_error_msg)

        with self.assertRaises(KeyError) as error:
            NearVector({"INVALID": "Some_concept"})
        check_error_message(self, error, vector_error_msg)

        with self.assertRaises(TypeError) as error:
            NearVector({"vector": set("Some_concept")})
        check_error_message(self, error, vector_value_error_msg)

        ## test "certainty"
        with self.assertRaises(TypeError) as error:
            NearVector({"vector": [1.0, 2.0, 3.0, 4.0], "certainty": "0.5"})
        check_error_message(self, error, certainty_error_msg(str))

        # test valid calls
        NearVector({"vector": [1.0, 2.0, 3.0, 4.0]})
        NearVector({"vector": [1.0, 2.0, 3.0, 4.0], "certainty": 0.75})

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        near_vector = NearVector({"vector": [1.0, 2.0, 3.0, 4.0]})
        self.assertEqual(str(near_vector), "nearVector: {vector: [1.0, 2.0, 3.0, 4.0]} ")
        near_vector = NearVector({"vector": [1.0, 2.0, 3.0, 4.0], "certainty": 0.75})
        self.assertEqual(
            str(near_vector), "nearVector: {vector: [1.0, 2.0, 3.0, 4.0] certainty: 0.75} "
        )


class TestNearObject(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # invalid calls

        ## error messages
        content_error_msg = lambda dt: f"NearObject filter is expected to be type dict but is {dt}"
        beacon_id_error_msg = "The 'content' argument should contain EITHER `id` OR `beacon`!"
        beacon_id_type_error_msg = lambda what, dt: (
            f"'{what}' key-value is expected to be of type <class 'str'> but is {dt}!"
        )
        certainty_error_msg = lambda dtype: (
            f"'certainty' key-value is expected to be of type <class 'float'> but is {dtype}!"
        )

        with self.assertRaises(TypeError) as error:
            NearObject(123, is_server_version_14=False)
        check_error_message(self, error, content_error_msg(int))

        with self.assertRaises(ValueError) as error:
            NearObject({"id": 123, "beacon": 456}, is_server_version_14=False)
        check_error_message(self, error, beacon_id_error_msg)

        with self.assertRaises(TypeError) as error:
            NearObject(
                {
                    "id": 123,
                },
                is_server_version_14=False,
            )
        check_error_message(self, error, beacon_id_type_error_msg("id", int))

        with self.assertRaises(TypeError) as error:
            NearObject(
                {
                    "beacon": {123},
                },
                is_server_version_14=False,
            )
        check_error_message(self, error, beacon_id_type_error_msg("beacon", set))

        with self.assertRaises(TypeError) as error:
            NearObject({"beacon": "test_beacon", "certainty": False}, is_server_version_14=False)
        check_error_message(self, error, certainty_error_msg(bool))

        # valid calls

        NearObject(
            {
                "id": "test_id",
            },
            is_server_version_14=False,
        )

        NearObject({"beacon": "test_beacon", "certainty": 0.7}, is_server_version_14=False)

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        near_object = NearObject(
            {
                "id": "test_id",
            },
            is_server_version_14=False,
        )
        self.assertEqual(str(near_object), 'nearObject: {id: "test_id"} ')

        near_object = NearObject({"id": "test_id", "certainty": 0.7}, is_server_version_14=False)
        self.assertEqual(str(near_object), 'nearObject: {id: "test_id" certainty: 0.7} ')

        near_object = NearObject(
            {
                "beacon": "test_beacon",
            },
            is_server_version_14=False,
        )
        self.assertEqual(str(near_object), 'nearObject: {beacon: "test_beacon"} ')

        near_object = NearObject(
            {"beacon": "test_beacon", "certainty": 0.0}, is_server_version_14=False
        )
        self.assertEqual(str(near_object), 'nearObject: {beacon: "test_beacon" certainty: 0.0} ')


class TestNearImage(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # invalid calls

        ## error messages
        content_error_msg = lambda dt: f"NearImage filter is expected to be type dict but is {dt}"
        image_key_error_msg = '"content" is missing the mandatory key "image"!'
        image_value_error_msg = (
            lambda dt: f"'image' key-value is expected to be of type <class 'str'> but is {dt}!"
        )
        certainty_error_msg = lambda dtype: (
            f"'certainty' key-value is expected to be of type <class 'float'> but is {dtype}!"
        )

        with self.assertRaises(TypeError) as error:
            NearImage(123)
        check_error_message(self, error, content_error_msg(int))

        with self.assertRaises(ValueError) as error:
            NearImage({"id": "image_path.png", "certainty": 456})
        check_error_message(self, error, image_key_error_msg)

        with self.assertRaises(TypeError) as error:
            NearImage({"image": True})
        check_error_message(self, error, image_value_error_msg(bool))

        with self.assertRaises(TypeError) as error:
            NearImage({"image": b"True"})
        check_error_message(self, error, image_value_error_msg(bytes))

        with self.assertRaises(TypeError) as error:
            NearImage({"image": "the_encoded_image", "certainty": False})
        check_error_message(self, error, certainty_error_msg(bool))

        # valid calls

        NearImage(
            {
                "image": "test_image",
            }
        )

        NearImage({"image": "test_image_2", "certainty": 0.7})

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        near_object = NearImage(
            {
                "image": "test_image",
            }
        )
        self.assertEqual(str(near_object), 'nearImage: {image: "test_image"} ')

        near_object = NearImage({"image": "test_image", "certainty": 0.7})
        self.assertEqual(str(near_object), 'nearImage: {image: "test_image" certainty: 0.7} ')


class TestWhere(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        content_error_msg = lambda dt: f"Where filter is expected to be type dict but is {dt}"
        content_key_error_msg = "Filter is missing required fields `path` or `operands`. Given: "
        path_key_error = "Filter is missing required field `operator`. Given: "
        dtype_no_value_error_msg = "Filter is missing required field 'value<TYPE>': "
        dtype_multiple_value_error_msg = "Multiple fields 'value<TYPE>' are not supported: "

        with self.assertRaises(TypeError) as error:
            Where(None)
        check_error_message(self, error, content_error_msg(type(None)))

        with self.assertRaises(TypeError) as error:
            Where("filter")
        check_error_message(self, error, content_error_msg(str))

        with self.assertRaises(ValueError) as error:
            Where({})
        check_startswith_error_message(self, error, content_key_error_msg)

        with self.assertRaises(ValueError) as error:
            Where({"path": "some_path"})
        check_startswith_error_message(self, error, path_key_error)

        with self.assertRaises(ValueError) as error:
            Where({"path": "some_path", "operator": "Like"})
        check_startswith_error_message(self, error, dtype_no_value_error_msg)

        with self.assertRaises(ValueError) as error:
            Where({"path": "some_path", "operator": "Like", "valueBoolean": True, "valueInt": 1})
        check_startswith_error_message(self, error, dtype_multiple_value_error_msg)

        with self.assertRaises(ValueError) as error:
            Where({"operands": "some_path"})
        check_startswith_error_message(self, error, path_key_error)

        with self.assertRaises(TypeError) as error:
            Where({"operands": "some_path", "operator": "Like"})
        check_error_message(self, error, content_error_msg(str))

        with self.assertRaises(TypeError) as error:
            Where({"operands": ["some_path"], "operator": "Like"})
        check_error_message(self, error, content_error_msg(str))

        # test valid calls
        Where({"path": "hasTheOneRing", "operator": "Equal", "valueBoolean": False})
        Where(
            {
                "operands": [
                    {"path": "hasTheOneRing", "operator": "Equal", "valueBoolean": False},
                    {"path": "hasFriend", "operator": "Equal", "valueText": "Samwise Gamgee"},
                ],
                "operator": "And",
            }
        )

    def test___str__(self):
        """
        Test the `__str__` method.
        """

        test_filter = {"path": ["name"], "operator": "Equal", "valueString": "A"}
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueString: "A"} ', result)

        test_filter = {
            "operator": "Or",
            "operands": [
                {"path": ["name"], "operator": "Equal", "valueString": "Alan Truing"},
                {"path": ["name"], "operator": "Equal", "valueString": "John von Neumann"},
            ],
        }
        result = str(Where(test_filter))
        self.assertEqual(
            'where: {operator: Or operands: [{path: ["name"] operator: Equal valueString: "Alan Truing"}, {path: ["name"] operator: Equal valueString: "John von Neumann"}]} ',
            result,
        )

        # test dataTypes
        test_filter = helper_get_test_filter("valueText", "Test")
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueText: "Test"} ', result)

        test_filter = helper_get_test_filter("valueString", "Test")
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueString: "Test"} ', result)

        test_filter = helper_get_test_filter("valueInt", 1)
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueInt: 1} ', result)

        test_filter = helper_get_test_filter("valueNumber", 1.4)
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueNumber: 1.4} ', result)

        test_filter = helper_get_test_filter("valueBoolean", True)
        result = str(Where(test_filter))
        self.assertEqual('where: {path: ["name"] operator: Equal valueBoolean: true} ', result)

        test_filter = helper_get_test_filter("valueDate", "test-2021-02-02")
        result = str(Where(test_filter))
        self.assertEqual(
            'where: {path: ["name"] operator: Equal valueDate: "test-2021-02-02"} ', result
        )

        geo_range = {
            "geoCoordinates": {"latitude": 51.51, "longitude": -0.09},
            "distance": {"max": 2000},
        }
        test_filter = helper_get_test_filter("valueGeoRange", geo_range)
        result = str(Where(test_filter))
        self.assertEqual(
            'where: {path: ["name"] operator: Equal valueGeoRange: {"geoCoordinates": {"latitude": 51.51, "longitude": -0.09}, "distance": {"max": 2000}}} ',
            str(result),
        )


class TestAskFilter(unittest.TestCase):
    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # test exceptions
        ## error messages
        content_type_msg = lambda dt: f"Ask filter is expected to be type dict but is {dt}"
        question_value_msg = 'Mandatory "question" key not present in the "content"!'
        question_type_msg = (
            lambda dt: f"'question' key-value is expected to be of type <class 'str'> but is {dt}!"
        )
        certainty_type_msg = (
            lambda dt: f"'certainty' key-value is expected to be of type <class 'float'> but is {dt}!"
        )
        properties_type_msg = (
            lambda dt: f"'properties' key-value is expected to be of type (<class 'list'>, <class 'str'>) but is {dt}!"
        )
        autocorrect_type_msg = (
            lambda dt: f"'autocorrect' key-value is expected to be of type <class 'bool'> but is {dt}!"
        )

        with self.assertRaises(TypeError) as error:
            Ask(None)
        check_error_message(self, error, content_type_msg(type(None)))

        with self.assertRaises(ValueError) as error:
            Ask({"certainty": 0.1})
        check_error_message(self, error, question_value_msg)

        with self.assertRaises(TypeError) as error:
            Ask({"question": ["Who is the president of USA?"]})
        check_error_message(self, error, question_type_msg(list))

        with self.assertRaises(TypeError) as error:
            Ask({"question": "Who is the president of USA?", "certainty": "1.0"})
        check_error_message(self, error, certainty_type_msg(str))

        with self.assertRaises(TypeError) as error:
            Ask({"question": "Who is the president of USA?", "autocorrect": {"True"}})
        check_error_message(self, error, autocorrect_type_msg(set))

        with self.assertRaises(TypeError) as error:
            Ask(
                {
                    "question": "Who is the president of USA?",
                    "certainty": 0.8,
                    "properties": ("prop1", "prop2"),
                }
            )
        check_error_message(self, error, properties_type_msg(tuple))

        # valid calls

        content = {
            "question": "Who is the president of USA?",
        }
        ask = Ask(content=content)
        self.assertEqual(str(ask), f"ask: {{question: \"{content['question']}\"}} ")

        content = {
            "question": "Who is the president of USA?",
            "certainty": 0.8,
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f"ask: {{question: \"{content['question']}\""
                f' certainty: {content["certainty"]}}} '
            ),
        )

        content = {
            "question": 'Who is the president of "USA"?',
            "certainty": 0.8,
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f'ask: {{question: "Who is the president of \\"USA\\"?"'
                f' certainty: {content["certainty"]}}} '
            ),
        )

        content = {
            "question": "Who is the president of USA?",
            "certainty": 0.8,
            "properties": "prop1",
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f"ask: {{question: \"{content['question']}\""
                f' certainty: {content["certainty"]}'
                f' properties: ["prop1"]}} '
            ),
        )

        content = {
            "question": "Who is the president of USA?",
            "certainty": 0.8,
            "properties": ["prop1", "prop2"],
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f"ask: {{question: \"{content['question']}\""
                f' certainty: {content["certainty"]}'
                f' properties: ["prop1", "prop2"]}} '
            ),
        )

        content = {
            "question": "Who is the president of USA?",
            "certainty": 0.8,
            "properties": ["prop1", "prop2"],
            "autocorrect": True,
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f"ask: {{question: \"{content['question']}\""
                f' certainty: {content["certainty"]}'
                ' properties: ["prop1", "prop2"] autocorrect: true} '
            ),
        )

        content = {"question": "Who is the president of USA?", "autocorrect": False}
        ask = Ask(content=content)
        self.assertEqual(
            str(ask), (f"ask: {{question: \"{content['question']}\" autocorrect: false}} ")
        )

        content = {
            "question": "Who is the president of USA?",
            "certainty": 0.8,
            "properties": ["prop1", "prop2"],
            "autocorrect": True,
            "rerank": True,
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask),
            (
                f"ask: {{question: \"{content['question']}\""
                f' certainty: {content["certainty"]}'
                ' properties: ["prop1", "prop2"] autocorrect: true'
                " rerank: true} "
            ),
        )

        content = {
            "question": "Who is the president of USA?",
            "rerank": False,
        }
        ask = Ask(content=content)
        self.assertEqual(
            str(ask), (f"ask: {{question: \"{content['question']}\"" " rerank: false} ")
        )
