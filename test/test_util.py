import unittest
from unittest.mock import patch, Mock
from weaviate.util import * 
from weaviate.util import  _get_dict_from_object, _is_sub_schema, _get_valid_timeout_config
from test.util import check_startswith_error_message, check_error_message


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

        type_error_message = "Expected to_object_uuid of type str"
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
        path = "https://raw.githubusercontent.com/semi-technologies/weaviate-python-client/weaviate_v1/test/schema/schema_company.json"
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

        result = get_valid_uuid("1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual(result, "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        # invalid formats
        type_error_message = "'uuid' must be of type str but was: "
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
        self.assertTrue(_is_sub_schema(schema_sub_set, schema_set))
        self.assertTrue(_is_sub_schema({}, schema_set))

        self.assertFalse(_is_sub_schema(disjoint_set, schema_set))
        self.assertFalse(_is_sub_schema(partial_set, schema_set))
        self.assertFalse(_is_sub_schema(schema_set_extended_prop, schema_set))

    def test__get_valid_timeout_config(self):
        """
        Test the `_get_valid_timeout_config` function.
        """

        # incalid calls 
        type_error_message = "'timeout_config' should be either a tuple or a list!"
        value_error_message = "'timeout_config' must be of length 2!"
        value_types_error_message = "'timeout_config' must be tupel of int"
        ## wrong type, None
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(None)
        check_error_message(self, error, type_error_message)

        ## wrong type, not list or tuple
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config("(2, 13)")
        check_error_message(self, error, type_error_message)

        ## worng tuple length 3
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((1,2,3))
        check_error_message(self, error, value_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config([1, 2, 3])
        check_error_message(self, error, value_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(tuple([1]))
        check_error_message(self, error, value_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config([1])
        check_error_message(self, error, value_error_message)

        ## wrong value types
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config([1, 10.123])
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(["1", 10])
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(["1", "10"])
        check_error_message(self, error, value_types_error_message)

        # valid calls
        _get_valid_timeout_config((2, 20))
        _get_valid_timeout_config([20, 10])
