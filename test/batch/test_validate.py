import unittest
from test.util import check_error_message
from unittest.mock import patch

from weaviate import ObjectsBatchRequest
from weaviate.batch.validate import TYPE_MAPPINGS, validate_data_object

_COMPLETE_PROPERTIES = [
    {"dataType": ["string"], "name": "test-string"},
    {"dataType": ["int"], "name": "test-int"},
    {"dataType": ["boolean"], "name": "test-bool"},
    {"dataType": ["number"], "name": "test-float"},
    {"dataType": ["date"], "name": "test-date"},
    {"dataType": ["geoCoordinates"], "name": "test-geo"},
    {"dataType": ["phoneNumber"], "name": "test-phone"},
    {"dataType": ["blob"], "name": "test-blob"},
]

_COMPLETE_SCHEMA = {
    "classes": [
        {
            "class": "Paper",
            "invertedIndexConfig": {"cleanupIntervalSeconds": 60},
            "properties": [
                {"dataType": ["string"], "name": "test-string"},
                {"dataType": ["int"], "name": "test-int"},
                {"dataType": ["boolean"], "name": "test-bool"},
                {"dataType": ["number"], "name": "test-float"},
                {"dataType": ["date"], "name": "test-date"},
                {"dataType": ["geoCoordinates"], "name": "test-geo"},
                {"dataType": ["phoneNumber"], "name": "test-phone"},
                {"dataType": ["blob"], "name": "test-blob"},
            ],
            "vectorIndexConfig": {
                "skip": False,
                "cleanupIntervalSeconds": 300,
                "maxConnections": 64,
                "efConstruction": 128,
                "ef": -1,
                "vectorCacheMaxObjects": 2000000,
            },
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
        }
    ]
}


class TestDataObjectValidation(unittest.TestCase):
    def test_data_object_validation_all_types(self):
        "Test the `validate_data_object()` function"

        data_object = {
            "test-string": "this is a string",
            "test-int": 123,
            "test-bool": True,
            "test-float": 123.456,
            "test-date": "1985-04-12T23:20:50.52Z",
            "test-geo": {"latitude": 45.5, "longitude": -122.3},
            "test-phone": {"input": "+4412345678"},
            "test-blob": "iVBORw0KGgoAAAANS",
        }

        self.assertEqual(True, validate_data_object(data_object, _COMPLETE_PROPERTIES))

    def test_data_object_validation_unknown_object(self):
        "Test the `validate_data_object()` function"
        data_object = {
            "test-string": "this is a string",
            "test-int": 123,
            "test-bool": True,
            "test-float": 123.456,
            "test-date": "1985-04-12T23:20:50.52Z",
            "test-geo": {"latitude": 45.5, "longitude": -122.3},
            "test-phone": {"input": "+4412345678"},
            "test-blob": "iVBORw0KGgoAAAANS",
            "unknown": "unknown",
        }

        error_message = "Invalid key: `unknown`"

        with self.assertRaises(ValueError) as error:
            validate_data_object(data_object, _COMPLETE_PROPERTIES)
        check_error_message(self, error, error_message)

    def test_properties_type_not_in_accepted_types(self):
        "Test the `validate_data_object()` function"
        properties = [{"dataType": ["unknown"], "name": "test-unknown"}]
        data_object = {"test-unknown": 123}

        error_message = "Unsupported type `unknown`"
        with self.assertRaises(ValueError) as error:
            validate_data_object(data_object, properties)
        check_error_message(self, error, error_message)

    def test_data_object_valid_date(self):
        "Test the `validate_data_object()` function"
        data_object = {"test-date": "1985-04-12T23:20:50.52Z"}

        self.assertEqual(True, validate_data_object(data_object, _COMPLETE_PROPERTIES))

    def test_data_object_invalid_date(self):
        "Test the `validate_data_object()` function"

        invalid_dates_data_objects = [
            {"test-date": "01-04-1984T23:20:50.52"},
            {"test-date": "01-04-1984"},
            {"test-date": "12-04-1984T23:20:50.52Z"},
            {"test-date": "12-March-1984"},
        ]
        error_message = "Invalid date: `{}`"

        for obj in invalid_dates_data_objects:
            with self.assertRaises(ValueError) as error:
                validate_data_object(obj, _COMPLETE_PROPERTIES)
            check_error_message(self, error, error_message.format(obj["test-date"]))

    def test_data_object_valid_geo_coordinates(self):
        "Test the `validate_data_object()` function"
        data_object = {"test-geo": {"latitude": 45.5, "longitude": -122.3}}

        self.assertEqual(True, validate_data_object(data_object, _COMPLETE_PROPERTIES))

    def test_data_object_invalid_geo_coordinates(self):
        "Test the `validate_data_object()` function"
        invalid_geo_coordinates_data_objects = [
            {"test-geo": {"latitude": 45.5, "unknown": -122.3}},
            {"test-geo": {"lat": 45.5, "long": -122.3}},
        ]
        error_message = "Invalid geoCoordinates: `{}`"

        for obj in invalid_geo_coordinates_data_objects:
            with self.assertRaises(ValueError) as error:
                validate_data_object(obj, _COMPLETE_PROPERTIES)
            check_error_message(self, error, error_message.format(obj["test-geo"]))

    def test_data_object_valid_phone_number(self):
        "Test the `validate_data_object()` function"
        data_object = {"test-phone": {"input": "+4412345678"}}

        self.assertEqual(True, validate_data_object(data_object, _COMPLETE_PROPERTIES))

    def test_data_object_valid_national_phone_number(self):
        "Test the `validate_data_object()` function"
        data_object = {"test-phone": {"input": "0123456789", "defaultCountry": "GB"}}

        self.assertEqual(True, validate_data_object(data_object, _COMPLETE_PROPERTIES))

    def test_data_object_invalid_national_phone_number(self):
        "Test the `validate_data_object()` function"
        invalid_phone_number_data_objects = [
            {"test-phone": {"input": "0123456789"}},
            {"test-phone": {"input": "00440123456789"}},
            {"test-phone": {"input": "003530123456789"}},
        ]
        error_message = "Invalid phoneNumber: `{}`"

        for obj in invalid_phone_number_data_objects:
            with self.assertRaises(ValueError) as error:
                validate_data_object(obj, _COMPLETE_PROPERTIES)
            check_error_message(self, error, error_message.format(obj["test-phone"]))

    def test_data_object_type_mismatch(self):
        "Test the `validate_data_object()` function"
        data_object = {"test-string": 123}

        error_message = "Invalid value: `{}` expected type `{}` but got type `{}`"
        with self.assertRaises(ValueError) as error:
            validate_data_object(data_object, _COMPLETE_PROPERTIES)
        check_error_message(
            self, error, error_message.format(123, "<class 'str'>", type(123))
        )


class TestObjectsBatchRequestWithValidationInit(unittest.TestCase):
    def test_batch_request_object_with_schema(self):
        "Test the `ObjectsBatchRequest` class with schema passed"
        batch_request = ObjectsBatchRequest(
            schema=_COMPLETE_SCHEMA,
        )

        self.assertEqual(batch_request.schema, _COMPLETE_SCHEMA)

    def test_batch_request_object_add_method(self):
        "Test the `ObjectsBatchRequest` class add method"
        batch_request = ObjectsBatchRequest(
            schema=_COMPLETE_SCHEMA,
        )

        res = batch_request.add(
            {
                "test-string": "test-string",
                "test-int": 123,
                "test-geo": {"latitude": 45.5, "longitude": -122.3},
                "test-date": "1985-04-12T23:20:50.52Z",
                "test-phone": {"input": "+4412345678", "defaultCountry": "GB"},
            },
            "Paper",
            validate_data=True,
        )

        self.assertEqual(res, None)

        self.assertEqual(
            batch_request._objects[0]["properties"],
            {
                "test-string": "test-string",
                "test-int": 123,
                "test-geo": {"latitude": 45.5, "longitude": -122.3},
                "test-date": "1985-04-12T23:20:50.52Z",
                "test-phone": {"input": "+4412345678", "defaultCountry": "GB"},
            },
        )

    def test_add_method_invalid_object_validation_enabled_no_schema(self):
        "Test the `ObjectsBatchRequest` class add method with validation enabled and no schema"
        batch_request = ObjectsBatchRequest()

        res = batch_request.add(
            {
                "test-string": 123,
                "test-int": "123",
                "test-geo": {"latitude": 45.5, "longitude": -122.3},
                "test-date": "1234",
                "test-phone": {"input": "4412345678"},
            },
            "Paper",
            validate_data=True,
        )

        self.assertEqual(res, None)

        self.assertEqual(
            batch_request._objects[0]["properties"],
            {
                "test-string": 123,
                "test-int": "123",
                "test-geo": {"latitude": 45.5, "longitude": -122.3},
                "test-date": "1234",
                "test-phone": {"input": "4412345678"},
            },
        )

    def test_add_method_invalid_object_validation_enabled_with_schema(self):
        "Test the `ObjectsBatchRequest` class add method with validation enabled and no schema"
        batch_request = ObjectsBatchRequest(
            schema=_COMPLETE_SCHEMA,
        )

        with self.assertRaises(ValueError):
            batch_request.add(
                {
                    "test-string": 123,
                    "test-int": "123",
                    "test-geo": {"latitude": 45.5, "longitude": -122.3},
                    "test-date": "1234",
                    "test-phone": {"input": "4412345678"},
                },
                "Paper",
                validate_data=True,
            )
