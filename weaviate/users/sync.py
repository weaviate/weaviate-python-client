from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.async_ import _UsersBase, _UsersAsync


@syncify.convert_new(_UsersAsync)
class _Users(_UsersBase[ConnectionSync]):
    pass
