import unittest
from copy import deepcopy
import uuid as uuid_lib
from unittest.mock import patch, Mock
from weaviate.util import  (
    generate_uuid5,
    image_decoder_b64,
    image_encoder_b64,
    generate_local_beacon,
    is_object_url,
    is_weaviate_object_url,
    get_vector,
    get_valid_uuid,
    get_domain_from_weaviate_url,
    _get_dict_from_object,
    _is_sub_schema,
    _get_valid_timeout_config,

)
from weaviate import SchemaValidationException
from test.util import check_error_message


schema_set = {
    "classes": [
        {
            "class": "Ollie",
            "properties": [{"name": "height"}]
        },
        {
            "class": "Shuvit",
            "properties": [{"name": "direction"}]
        },
        {
            "class": "Board",
            "properties": [{"name": "brand"},
                            {"name": "art"},
                            {"name": "size"}]
        },
        {
            "class": "Truck",
            "properties": [{"name": "name"},
                            {"name": "height"}]
        }
    ],
}

schema_set_extended_prop = {
    "classes": [
        {
            "class": "Ollie",
            "properties": [{"name": "height", "name": "weight"}]
        },
        {
            "class": "Shuvit",
            "properties": [{"name": "direction"}]
        },
        {
            "class": "Board",
            "properties": [{"name": "brand"},
                            {"name": "art"},
                            {"name": "size"}]
        },
        {
            "class": "Truck",
            "properties": [{"name": "name"},
                            {"name": "height"}]
        }
    ],
}

schema_sub_set = {
    "classes": [
        {
            "class": "Ollie",
            "properties": [{"name": "height"}]
        },
        {
            "class": "Board",
            "properties": [{"name": "brand"},
                            {"name": "art"},
                            {"name": "size"}]
        }
    ],
}

disjoint_set = {
    "classes": [
        {
            "class": "Manual",
            "properties": [{"name": "nose"}]
        },
        {
            "class": "Bearings",
            "properties": [{"name": "brand"}]
        }
    ],
}

partial_set = {
    "classes": [
        {
            "class": "Board",
            "properties": [{"name": "brand"},
                            {"name": "art"},
                            {"name": "size"}]
        },
        {
            "class": "Truck",
            "properties": [{"name": "name"},
                            {"name": "height"}]
        },
        {
            "class": "Bearings",
            "properties": [{"name": "brand"}]
        },
        {
            "class": "Ollie",
            "properties": [{"name": "height"}]
        },
        {
            "class": "Shuvit",
            "properties": [{"name": "direction"}]
        },
        {
            "class": "Manual",
            "properties": [{"name": "nose"}]
        }
    ],
}

schema_company = {
  "classes": [
    {
      "class": "Company",
      "description": "A business that acts in the market",
      "properties": [
        {
          "name": "name",
          "description": "The name under which the company is known",
          "dataType": ["text"]
        },
        {
          "name": "legalBody",
          "description": "The legal body under which the company maintains its business",
          "dataType": ["text"]
        },
        {
          "name": "hasEmployee",
          "description": "The employees of the company",
          "dataType": ["Employee"]
        }
      ]
    },
    {
      "class": "Employee",
      "description": "An employee of the company",
      "properties": [
        {
          "name": "name",
          "description": "The name of the employee",
          "dataType": ["text"]
        },
        {
          "name": "job",
          "description": "the job description of the employee",
          "dataType": ["text"]
        },
        {
          "name": "yearsInTheCompany",
          "description": "The number of years this employee has worked in the company",
          "dataType": ["int"]
        }
      ]
    }
  ]
}


class TestUtil(unittest.TestCase):

    def test_generate_local_beacon(self):
        """
        Test the `generate_local_beacon` function.
        """

        type_error_message = "Expected to_object_uuid of type str or uuid.UUID"
        value_error_message = "Uuid does not have the propper form"
        # wrong data type
        with self.assertRaises(TypeError) as error:
            generate_local_beacon(None)
        check_error_message(self, error, type_error_message)
        # wrong value
        with self.assertRaises(ValueError) as error:
            generate_local_beacon("Leeroy Jenkins")
        check_error_message(self, error, value_error_message)

        beacon = generate_local_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35a")
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/fcf33178-1b5d-5174-b2e7-04a2129dd35a")

        beacon = generate_local_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35b")
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/fcf33178-1b5d-5174-b2e7-04a2129dd35b")

        beacon = generate_local_beacon("fcf331781b5d5174b2e704a2129dd35b")
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/fcf33178-1b5d-5174-b2e7-04a2129dd35b")

        beacon = generate_local_beacon(uuid_lib.UUID("fcf33178-1b5d-5174-b2e7-04a2129dd35b"))
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/fcf33178-1b5d-5174-b2e7-04a2129dd35b")
        
        beacon = generate_local_beacon(uuid_lib.UUID("fcf331781b5d5174b2e704a2129dd35b"))
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/fcf33178-1b5d-5174-b2e7-04a2129dd35b")

    def test__get_dict_from_object(self):
        """
        Test the `_get_dict_from_object` function.
        """

        none_error_message = "argument is None"
        file_error_message = "No file found at location "
        url_error_message = "Could not download file "
        type_error_message = ("Argument is not of the supported types. Supported types are "
                    "url or file path as string or schema as dict.")
        # test wrong type None
        with self.assertRaises(TypeError) as error:
            _get_dict_from_object(None)
        check_error_message(self, error, none_error_message)
        # wrong data type
        with self.assertRaises(TypeError) as error:
            _get_dict_from_object([{"key": 1234}])
        check_error_message(self, error, type_error_message)
        # wrong path
        with self.assertRaises(ValueError) as error:
            _get_dict_from_object("not_a_path_or_url.txt")
        check_error_message(self, error, file_error_message + "not_a_path_or_url.txt")
        # wrong URL or non existing one or failure of requests.get
        with patch('weaviate.util.requests') as mock_obj:
            result_mock = Mock()
            result_mock.status_code = 404
            mock_obj.get.return_value = result_mock
            with self.assertRaises(ValueError) as error:
                _get_dict_from_object("http://www.url.com")
            check_error_message(self, error, url_error_message + "http://www.url.com")
            mock_obj.get.assert_called()

        # valid calls
        self.assertEqual(_get_dict_from_object({"key": "val"}), {"key": "val"})
        # read from file
        path = '/'.join(__file__.split('/')[:-1])
        self.assertEqual(_get_dict_from_object(f'{path}/schema/schema_company.json'), schema_company)
        # read from URL
        path = "https://raw.githubusercontent.com/semi-technologies/weaviate-python-client/main/test/schema/schema_company.json"
        self.assertEqual(_get_dict_from_object(path), schema_company)

    def test_is_weaviate_object_url(self):
        """
        Test the `is_weaviate_object_url` function.
        """

        # valid formats
        self.assertTrue(
            is_weaviate_object_url("weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertTrue(
            is_weaviate_object_url("weaviate://some-domain.com/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))

        # invalid formats
        ## wrong argument data type
        self.assertFalse(
            is_weaviate_object_url(["weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"]))
        ## wrong prefix, i.e. does not start with 'weaviate://' 
        self.assertFalse(
            is_weaviate_object_url("http://some-domain.com/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        ## wrong path, additional '/thing'
        self.assertFalse(
            is_weaviate_object_url("weaviate://localhost/things/f61b-b524-45e0-9bbe-2c1550bf73d2"))
        ## worng domain format
        self.assertFalse(
            is_weaviate_object_url("weaviate://some-INVALID-domain/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        # wrong UUID format
        self.assertFalse(
            is_weaviate_object_url("weaviate://localhost/UUID"))

    def test_is_object_url(self):
        """
        Test the `is_object_url` function.
        """

        # valid formats
        self.assertTrue(
            is_object_url("http://localhost:8080/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446"))
        self.assertTrue(
            is_object_url("http://ramalamadingdong/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446"))

        # invalid formats
        ## wrong path, should be at least 3 subpaths to the object UUID
        self.assertFalse(
            is_object_url("objects/1c9cd584-88fe-5010-83d0-017cb3fcb446"))
        ## wrong '/v2', shoudl be '/v1'  
        self.assertFalse(
            is_object_url("http://localhost:8080/v2/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446"))
        ## wrong UUID format
        self.assertFalse(
            is_object_url("http://ramalamadingdong/v1/objects/1c9cd584-88fe-5010-83d0"))
        ## wrong objects path, instead of '/passions' should have been '/objects/
        self.assertFalse(
            is_object_url("http://localhost:8080/v1/passions/1c9cd584-88fe-5010-83d0-017cb3fcb446"))

    def test_get_valid_uuid(self):
        """
        Test the `get_valid_uuid` function.
        """

        # valid calls
        result = get_valid_uuid("weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
        self.assertEqual(result, "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")

        result = get_valid_uuid("weaviate://otherhost.com/28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
        self.assertEqual(result, "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")

        result = get_valid_uuid("http://localhost:8080/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        result = get_valid_uuid("http://otherhost_2:8080/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        result = get_valid_uuid("http://otherhost_2:8080/v1/objects/1c9cd58488fe501083d0017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        result = get_valid_uuid("1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        result = get_valid_uuid("1c9cd58488fe501083d0017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        result = get_valid_uuid(uuid_lib.UUID("1c9cd58488fe501083d0017cb3fcb446"))
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        # invalid formats
        type_error_message = "'uuid' must be of type str or uuid.UUID, but was: "
        value_error_message = "Not valid 'uuid' or 'uuid' can not be extracted from value"
        ## neither an object URL nor a weaviate object URL
        with self.assertRaises(ValueError) as error:
            get_valid_uuid("http://localhost:8080/v1/1c9cd584-88fe-5010-83d0-017cb3fcb")
        check_error_message(self, error, value_error_message)

        # wrong UUID format
        with self.assertRaises(ValueError) as error:
            get_valid_uuid("http://localhost:8080/v1/objects/some-UUID")
        check_error_message(self, error, value_error_message)

        ## wrong '/v2', shoudl be '/v1'
        with self.assertRaises(ValueError) as error:
            get_valid_uuid("http://localhost:8080/v2/objects/1c9cd584-88fe-5010-83d0-017cb3fcb")
        check_error_message(self, error, value_error_message)

        ## wrong URL
        with self.assertRaises(ValueError) as error:
            get_valid_uuid("weaviate://INVALID_URL//1c9cd584-88fe-5010-83d0-017cb3fcb")
        check_error_message(self, error, value_error_message)

        ## wrong UUID data type
        with self.assertRaises(TypeError) as error:
            get_valid_uuid(12)
        check_error_message(self, error, type_error_message + str(int))

    def test_get_vector(self):
        """
        Test the `get_vector` function.
        """

        vector_list  = [1., 2., 3.]
        # vector is a list
        self.assertEqual(get_vector(vector_list), vector_list)

        # vector is a `torch.Tensor` or `numpy.ndarray`
        vector_mock = Mock()
        mock_tolist = Mock()
        mock_tolist.tolist.return_value = vector_list
        mock_squeeze = Mock(return_value = mock_tolist)
        vector_mock.squeeze = mock_squeeze
        self.assertEqual(get_vector(vector_mock), vector_list)

        # vector is a `tf.Tensor`
        vector_mock = Mock()
        mock_tolist = Mock()
        mock_squeeze = Mock()
        mock_tolist.tolist.return_value = vector_list
        mock_squeeze.squeeze.return_value = mock_tolist
        mock_numpy = Mock(return_value = mock_squeeze)
        vector_mock.numpy = mock_numpy
        vector_mock.squeeze = Mock(side_effect = AttributeError("TEST TensorFlow Tensor"))
        self.assertEqual(get_vector(vector_mock), vector_list)

        # invalid call
        type_error_message = ("The type of the 'vector' argument is not supported!\n"
                "Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` "
                "and `tf.Tensor`")
        with self.assertRaises(TypeError) as error:
            get_vector('[1., 2., 3.]')
        check_error_message(self, error, type_error_message)

    def test_get_domain_from_weaviate_url(self):
        """
        Test the `get_domain_from_weaviate_url` function.
        """

        uuid = "28f3f61b-b524-45e0-9bbe-2c1550bf73d2"
        self.assertEqual(get_domain_from_weaviate_url(f"weaviate://localhost/{uuid}"), "localhost")
        self.assertEqual(get_domain_from_weaviate_url(f"weaviate://otherhost/{uuid}"), "otherhost")

    def test__is_sub_schema(self):
        """
        Test the `_is_sub_schema` function.
        """

        self.assertTrue(_is_sub_schema(schema_set, schema_set))
        self.assertTrue(_is_sub_schema(schema_set['classes'][0], schema_set))
        self.assertTrue(_is_sub_schema(schema_sub_set, schema_set))

        schema_set_copy = deepcopy(schema_set)
        for schema_class in schema_set_copy['classes']:
            schema_class['class'] = schema_class['class'].lower()
        self.assertTrue(_is_sub_schema(schema_set_copy, schema_set))
        self.assertTrue(_is_sub_schema(schema_set, schema_set_copy))
        self.assertTrue(_is_sub_schema(schema_set_copy, schema_set_copy))

        self.assertFalse(_is_sub_schema({'class': 'A'}, schema_set))
        self.assertFalse(_is_sub_schema(disjoint_set, schema_set))
        self.assertFalse(_is_sub_schema(partial_set, schema_set))
        self.assertFalse(_is_sub_schema(schema_set_extended_prop, schema_set))

        # invalid calls

        invalid_sub_schema_msg = "The sub schema class/es MUST have a 'class' keyword each!"

        with self.assertRaises(SchemaValidationException) as error:
            _is_sub_schema({}, schema_set)
        check_error_message(self, error, invalid_sub_schema_msg)

    def test__get_valid_timeout_config(self):
        """
        Test the `_get_valid_timeout_config` function.
        """

        # incalid calls
        negative_num_error_message = "'timeout_config' cannot be non-positive number/s!"
        type_error_message = "'timeout_config' should be a (or tuple of) positive real number/s!"
        value_error_message = "'timeout_config' must be of length 2!"
        value_types_error_message = "'timeout_config' must be tuple of real numbers"

        ## wrong type
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(None)
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(True)
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config("(2, 13)")
        check_error_message(self, error, type_error_message)

        ## wrong tuple length 3
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((1,2,3))
        check_error_message(self, error, value_error_message)

        ## wrong value types
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config((None, None))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(("1", 10))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(("1", "10"))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config((True, False))
        check_error_message(self, error, value_types_error_message)

        ## non-positive numbers
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(0)
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(-1)
        check_error_message(self, error, negative_num_error_message)
        
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(-4.134)
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((-3.5, 1.5))
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((3, -1.5))
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((0, 0))
        check_error_message(self, error, negative_num_error_message)

        # valid calls
        self.assertEqual(_get_valid_timeout_config((2, 20)), (2, 20))
        self.assertEqual(_get_valid_timeout_config((3.5, 2.34)), (3.5, 2.34))
        self.assertEqual(_get_valid_timeout_config(4.32), (4.32, 4.32))
        

    def test_image_encoder_b64(self):
        """
        Test the `image_encoder_b64` function.
        """


        encode_weaviate_logo_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAZAAAAE5CAYAAAC+rHbqAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMTQ1IDc5LjE2MzQ5OSwgMjAxOC8wOC8xMy0xNjo0MDoyMiAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTkgKE1hY2ludG9zaCkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6Rjc3MkEzQzdGM0QxMTFFODlBRTRBNjMyNUE2MTk3NzgiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6Rjc3MkEzQzhGM0QxMTFFODlBRTRBNjMyNUE2MTk3NzgiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpGNzcyQTNDNUYzRDExMUU4OUFFNEE2MzI1QTYxOTc3OCIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDpGNzcyQTNDNkYzRDExMUU4OUFFNEE2MzI1QTYxOTc3OCIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/PnOiDKoAABWzSURBVHja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'
        file_path_value_error_message = "No file found at location non-existingfile.png"
        type_error_message = ('"image_or_image_path" should be a image path or a binary read file'
                            ' (io.BufferedReader)')

        # invalid calls
        with self.assertRaises(ValueError) as error:
            image_encoder_b64('non-existingfile.png')
        check_error_message(self, error, file_path_value_error_message)

        with self.assertRaises(TypeError) as error:
            image_encoder_b64(True)
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            with open('image.png', 'wb') as file:
                image_encoder_b64(file)
        check_error_message(self, error, type_error_message)

        # valid calls
        encrypted_1 = image_encoder_b64('integration/weaviate-logo.png')
        self.assertEqual(encrypted_1, encode_weaviate_logo_b64)
        self.assertIsInstance(encrypted_1, str)

        with open('integration/weaviate-logo.png', 'rb') as file:
            encrypted_2 = image_encoder_b64(file)
        self.assertEqual(encrypted_2, encode_weaviate_logo_b64)
        self.assertIsInstance(encrypted_2, str)

    def test_image_decoder_b64(self):
        """
        Test the `image_decoder_b64` function.
        """

        encode_weaviate_logo_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAZAAAAE5CAYAAAC+rHbqAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMTQ1IDc5LjE2MzQ5OSwgMjAxOC8wOC8xMy0xNjo0MDoyMiAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTkgKE1hY2ludG9zaCkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6Rjc3MkEzQzdGM0QxMTFFODlBRTRBNjMyNUE2MTk3NzgiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6Rjc3MkEzQzhGM0QxMTFFODlBRTRBNjMyNUE2MTk3NzgiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpGNzcyQTNDNUYzRDExMUU4OUFFNEE2MzI1QTYxOTc3OCIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDpGNzcyQTNDNkYzRDExMUU4OUFFNEE2MzI1QTYxOTc3OCIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/PnOiDKoAABWzSURBVHja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'
        
        decoded = image_decoder_b64(encode_weaviate_logo_b64)

        with open('integration/weaviate-logo.png', 'rb') as file:
            self.assertEqual(decoded, file.read())
            self.assertIsInstance(decoded, bytes)
    @patch('weaviate.util.uuid_lib')
    def test_generate_uuid5(self, mock_uuid):

        result = generate_uuid5('TestID!', 'Test!')
        self.assertIsInstance(result, str)
        mock_uuid.uuid5.assert_called()
