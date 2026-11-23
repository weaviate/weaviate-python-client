from setuptools import setup
from setuptools_scm import get_version

# [grpc-web] pins weaviate-client-web to this build's version (lockstep: see
# packages/web/setup.py); micropip does not backtrack to find a matching pair.
version = get_version(root=".", relative_to=__file__)

if __name__ == "__main__":
    setup(
        extras_require={
            "agents": ["weaviate-agents >=1.0.0, <2.0.0"],
            "grpc-web": [f'weaviate-client-web=={version}; sys_platform == "emscripten"'],
        }
    )
