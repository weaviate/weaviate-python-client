from typing import List

from weaviate import WeaviateAsyncClient, WeaviateClient, connect_to_local, use_async_with_local
from weaviate.classes.config import Configure, DataType, Property


class SyncJourneys:
    def __init__(self, client: WeaviateClient) -> None:
        self.__client = client

    @classmethod
    def use(cls) -> "SyncJourneys":
        return cls(connect_to_local(port=8090, grpc_port=50061))

    def close(self) -> None:
        self.__client.close()

    def simple(self) -> List[dict]:
        name = "FastAPISyncTestingCollection"
        if self.__client.collections.exists(name):
            self.__client.collections.delete(name)
        collection = self.__client.collections.create(
            name=name,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
        )
        with collection.batch.dynamic() as batch:
            for i in range(1000):
                batch.add_object({"name": f"Person {i}", "age": i})
        res = collection.query.fetch_objects(limit=100)
        self.__client.collections.delete(name)
        return [obj.properties for obj in res.objects]


class AsyncJourneys:
    def __init__(self, client: WeaviateAsyncClient) -> None:
        self.__client = client

    @classmethod
    async def use(cls) -> "AsyncJourneys":
        client = use_async_with_local(port=8090, grpc_port=50061)
        await client.connect()
        return cls(client)

    async def close(self) -> None:
        await self.__client.close()

    async def simple(self) -> List[dict]:
        name = "FastAPIAsyncTestingCollection"
        if await self.__client.collections.exists(name):
            await self.__client.collections.delete(name)
        collection = await self.__client.collections.create(
            name=name,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
        )
        await collection.data.insert_many([{"name": f"Person {i}", "age": i} for i in range(100)])
        res = await collection.query.fetch_objects(limit=1000)
        await self.__client.collections.delete(name)
        return [obj.properties for obj in res.objects]
