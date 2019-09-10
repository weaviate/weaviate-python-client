from setuptools import setup


REQUIRES = [
    "requests>=2.22.0",
]

setup(name="weaviate-client",
      version="0.0.0",
      description="A python weaviate client",
      packages=["weaviate", "weaviate.connect"])
