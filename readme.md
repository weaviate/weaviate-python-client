# Weaviate python client  <img alt='Weaviate logo' src='https://raw.githubusercontent.com/semi-technologies/weaviate/19de0956c69b66c5552447e84d016f4fe29d12c9/docs/assets/weaviate-logo.png' width='180' align='right' />

A python client for easy abstracted interaction with a weaviate instance.

## Install

The package can be easily installed using pip. The client is developed and tested for python 3.7. 

```shell script
git clone git@github.com:semi-technologies/weaviate-python-client.git
cd weaviate-python-client

# Virtualenv users may need to switch into the desired environment first
pip install .
```

## Usage

```python
from weaviate import Weaviate

weaviate_instance = Weaviate("http://localhost:8080")
city = {"name": "Amsterdam"}

weaviate_instance.create_thing(city, "City")
```

## Build Status

[![Build Status](https://travis-ci.com/semi-technologies/weaviate-python-client.svg?token=1qdvi3hJanQcWdqEstmy&branch=master)](https://travis-ci.com/semi-technologies/weaviate-python-client)


