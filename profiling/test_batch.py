# run:
# - profiling: pytest -m profiling profiling/test_batch.py --profile-svg
# - benchmark: pytest profiling/test_profiling.py --benchmark-only --benchmark-disable-gc
import gc
import linecache
import tracemalloc

import objgraph
import weaviate

from pympler import asizeof
from numpy import random
from tqdm import tqdm
from weaviate.classes.config import DataType, Property
from weaviate.collections import Collection

HOW_MANY = 200000


def random_str() -> str:
    return "".join([chr(random.randint(97, 123)) for _ in range(10)])


def make_collection(client: weaviate.WeaviateClient, name: str) -> Collection:
    client.collections.delete(name)
    return client.collections.create(
        name=name,
        properties=[
            Property(name="a", data_type=DataType.TEXT),
            Property(name="b", data_type=DataType.TEXT),
            Property(name="c", data_type=DataType.TEXT),
            Property(name="d", data_type=DataType.TEXT),
            Property(name="e", data_type=DataType.TEXT),
        ],
    )


def ingest_fakes(collection_src: Collection) -> None:
    with collection_src.batch.dynamic() as batch:
        for i in range(HOW_MANY):
            if i % 10000 == 0:
                print(f"Ingested {i} objects")
                print(f"There are {len(gc.garbage)} objects that cannot be collected")
                # for obj in gc.garbage:
                #     print(f"Uncollectable: {obj}")
            batch.add_object(
                properties={
                    "a": random_str(),
                    "b": random_str(),
                    "c": random_str(),
                    "d": random_str(),
                    "e": random_str(),
                },
            )


def migrate_data_matt(collection_src: Collection, collection_tgt: Collection):
    with collection_tgt.batch.dynamic() as batch:
        i = 1
        for q in tqdm(collection_src.iterator(include_vector=False)):
            if i % 10000 == 0:
                print(f"Migrated {i} objects")
                print(f"There are {len(gc.garbage)} objects that cannot be collected")
                # for obj in gc.garbage:
                #     print(f"Uncollectable: {obj}")
            if i > HOW_MANY:
                break

            source_uuid = str(q.uuid)

            # Check if object exists in target collection
            try:
                obj = collection_tgt.query.fetch_object_by_id(uuid=source_uuid)
                if obj is not None:
                    continue
            except Exception as e:
                print(f"Error fetching object by ID: {e}")
                continue

            # Insert the new object
            try:
                batch.add_object(properties=q.properties, uuid=source_uuid)
            except Exception as e:
                print(f"Error adding object to batch: {e}")
                continue

            i += 1
    return i


def display_top(snapshot, key_type="lineno", limit=10):
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print("#%s: %s:%s: %.1f KiB" % (index, frame.filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def main() -> None:
    tracemalloc.start(10)
    objgraph.show_growth()
    gc.set_debug(gc.DEBUG_SAVEALL)
    with weaviate.connect_to_local() as _:
        # src = make_collection(client, 'src')
        # tgt = make_collection(client, 'tgt')
        # ingest_fakes(src)
        # print(migrate_data_matt(src, tgt))
        pass
    gc.collect()
    print(
        f"There are {len(gc.garbage)} objects that cannot be collected. Their total memory footprint is {asizeof.asizeof(gc.garbage)} bytes"
    )
    # for idx, obj in enumerate(gc.garbage):
    #     print(f"Uncollectable: {obj.__class__}\n{obj}")
    #     if obj.__class__ in [dict, list, tuple, deque, set]:
    #         continue
    #     objgraph.show_chain(
    #         objgraph.find_backref_chain(obj, objgraph.is_proper_module),
    #         filename=f"objgraphs-bw/refs_{idx}.png"
    #     )
    #     objgraph.show_refs(
    #         objgraph.find_ref_chain(obj, objgraph.is_proper_module),
    #         filename=f"objgraphs-fw/refs_{idx}.png"
    #     )
    objgraph.show_most_common_types()
    objgraph.show_growth()
    snapshot = tracemalloc.take_snapshot()
    display_top(snapshot)


if __name__ == "__main__":
    main()
