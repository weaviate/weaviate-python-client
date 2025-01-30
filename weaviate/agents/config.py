from typing import Any, Type

class WeaviateAuth:
    def __init__(self, weaviate_url: str, weaviate_api_key: str, extras: Any):
        self.weaviate_url = weaviate_url
        self.weaviate_api_key = weaviate_api_key
        self.extras = extras

class BigQueryAuth:
    def __init__(self, google_credentials_filepath: str):
        self.google_creds_path = google_credentials_filepath

class ExaAuth:
    def __init__(self, exa_api_key: str):
        self.exa_api_key = exa_api_key

class AuthRegistry:
    def __init__(self, auths=None):
        self._auths = {}
        self.register("weaviate", WeaviateAuth)
        self.register("bigquery", BigQueryAuth)
        self.register("exa", ExaAuth)
    
    def register(self, name: str, auth_class: Type) -> None:
        """Register a new authentication class"""
        self._auths[name.lower()] = auth_class
    
    def get(self, name: str) -> Type:
        """Get an authentication class by name"""
        return self._auths.get(name.lower())
    
    def unregister(self, name: str) -> None:
        """Remove an authentication class from the registry"""
        if name.lower() in self._auths:
            del self._auths[name.lower()]
