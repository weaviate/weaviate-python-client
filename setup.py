from builtins import open
from os import path
from setuptools import setup
from setuptools.command.egg_info import egg_info
from weaviate.version import __version__

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


class egg_info_ex(egg_info):
    """Includes license file into `.egg-info` folder."""

    def run(self):
        # don't duplicate license into `.egg-info` when building a distribution
        if not self.distribution.have_run.get('install', True):
            # `install` command is in progress, copy license
            self.mkpath(self.egg_info)
            self.copy_file('LICENSE.md', self.egg_info)

        egg_info.run(self)


setup(
  name="weaviate-client",
  version=__version__,
  description="A python native weaviate client",
  long_description=long_description,
  long_description_content_type='text/x-rst',
  author="SeMI Technologies",
  author_email="hello@semi.technology",
  packages=[
    "weaviate",
    "weaviate.connect",
    "weaviate.schema",
    "weaviate.schema.properties",
    "weaviate.batch",
    "weaviate.classification",
    "weaviate.contextionary",
    "weaviate.data",
    "weaviate.data.references",
    "weaviate.gql",
    "weaviate.wcs",
  ],
  python_requires='>=3.6',
  install_requires=[
    "requests>=2.23.0,<2.28.0",
    "validators>=0.18.2,<0.19.0",
    "tqdm>=4.59.0,<5.0.0"
  ],
  license_files = ('LICENSE.md',),
  cmdclass = {'egg_info': egg_info_ex},
)
