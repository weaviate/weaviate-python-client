import gc
import httpx
import objgraph
from collections import deque


def sync() -> None:
    with httpx.Client() as client:
        client.get("https://www.google.com")


# async def async_() -> None:
#     async with httpx.AsyncClient() as client:
#         await client.get("https://www.google.com")
#     gc.collect()
#     print("Uncollectible Garbage: ", len(gc.garbage))

if __name__ == "__main__":
    gc.set_debug(gc.DEBUG_SAVEALL)
    sync()
    gc.collect()
    print("Uncollectible Garbage: ", len(gc.garbage))
    for idx, obj in enumerate(gc.garbage):
        print(f"Uncollectable: {obj.__class__}\n{obj}")
        if obj.__class__ in [dict, list, tuple, deque, set]:
            continue
        objgraph.show_chain(
            objgraph.find_backref_chain(obj, objgraph.is_proper_module),
            filename=f"objgraphs-bw/refs_{idx}.png",
        )
        objgraph.show_refs(
            objgraph.find_ref_chain(obj, objgraph.is_proper_module),
            filename=f"objgraphs-fw/refs_{idx}.png",
        )
