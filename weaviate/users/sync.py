from weaviate import syncify

from weaviate.users.users import _UsersAsync


@syncify.convert
class _Users(_UsersAsync):
    pass
