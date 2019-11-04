# Weaviate python client  <img alt='Weaviate logo' src='https://raw.githubusercontent.com/semi-technologies/weaviate/19de0956c69b66c5552447e84d016f4fe29d12c9/docs/assets/weaviate-logo.png' width='180' align='right' />

A python native client for easy interaction with a weaviate instance.

## Install

The package can be easily installed using pip. The client is developed and tested for python 3.7. 

```shell script
pip install weaviate-client
```

## Usage

First make sure that weaviate is running. See the [installation guide](https://www.semi.technology/documentation/weaviate/current/installation.html) on how to start weaviate.


Before we can load data we need to create a client and load a schema.
```python
import weaviate
client = weaviate.Client("http://localhost:8080")
client.create_schema("https://raw.githubusercontent.com/semi-technologies/weaviate-python-client/master/documentation/getting_started/people_schema.json")
```
Now lets create some things.
```python
client.create_thing({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
client.create_thing({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")

client.create_thing({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")
```
We can simply add cross-references through:
```python
client.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "b36268d4-a6b5-5274-985f-45f13ce0c642")
client.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
```

*Note: Weaviate might needs a second to update its index after a new thing has been created.*

Look at the data using the simple query:
```graphql
{
  Get {
    Things {
      Group {
        name
        uuid
        Members {
          ... on Person {
            name
            uuid
          }
        }
      }
    }
  }
}
```


## Build Status

[![Build Status](https://travis-ci.com/semi-technologies/weaviate-python-client.svg?token=1qdvi3hJanQcWdqEstmy&branch=master)](https://travis-ci.com/semi-technologies/weaviate-python-client)


