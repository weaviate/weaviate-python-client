#!/bin/bash

python -m unittest test.add_reference_batch
python -m unittest test.add_thing
python -m unittest test.add_thing_batch
python -m unittest test.auth
python -m unittest test.c11y
python -m unittest test.client
python -m unittest test.delete
python -m unittest test.exceptions
python -m unittest test.is_reachable
python -m unittest test.patch_thing
python -m unittest test.query
python -m unittest test.schema
python -m unittest test.util
python -m unittest test.validate_schema
