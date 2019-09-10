### Install

The package can be easily installed using pip.   

```shell script
git clone git@github.com:semi-technologies/weaviate-python-client.git
cd weaviate-python-client

# pip3 in systems with 2.7 as default interpreter
# Virtualenv users may need to switch into the desired environment first
pip install .
```

### Usage

```python
from weaviate import Weaviate

weaviate_instance = Weaviate("http://localhost:8080")
city = {"name": "Amsterdam"}

weaviate_instance.create_thing(city, "City")
```




