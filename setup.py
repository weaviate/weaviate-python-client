from setuptools import setup


# REQUIRES = [
#     "requests>=2.22.0",
#     "validators>=0.14.0",
# ]

setup(name="weaviate-client",
      version="0.1.0",
      description="A python native weaviate client",
      long_description="""
      A client to interact with weaviate. 
      It allows to create schemas and classes and includes some other basic features of the weaviate REST API.
      Weaviate may be found here: https://github.com/semi-technologies/weaviate
      For bug reports and feature requests please use GitHub issues: 
      https://github.com/semi-technologies/weaviate-python-client/issues      
      """,
      author="SeMI Technologies",
      author_email="hello@semi.technology",
      packages=["weaviate", "weaviate.connect"],
      install_requires=[
        "requests>=2.22.0",
        "validators>=0.14.0",]),