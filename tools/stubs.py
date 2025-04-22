import ast
import inspect
import textwrap
from collections import defaultdict
from typing import Literal, cast


class ExecutorTransformer(ast.NodeTransformer):
    def __init__(self, colour: Literal["async", "sync"]):
        self.colour = colour
        self.executor_names = []

    def visit_ClassDef(self, node):
        self.executor_names.append(node.name)
        node.bases = self.__parse_generics(node)
        node.body = self.__parse_body(node)
        node.name = node.name.replace(
            "Executor", "" if self.colour == "sync" else self.colour.capitalize()
        )
        self.generic_visit(node)
        return node

    def __is_overload(self, fn: ast.FunctionDef):
        return any(isinstance(d, ast.Name) and d.id == "overload" for d in fn.decorator_list)

    def __parse_body(self, node: ast.ClassDef):
        funcs_by_name = defaultdict(list)
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs_by_name[stmt.name].append(stmt)

        new_body: list[ast.stmt] = []
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name.startswith("__"):
                continue  # Skip all dunder methods
            if isinstance(stmt, ast.FunctionDef):
                overloads = funcs_by_name[stmt.name]
                if any(self.__is_overload(f) for f in overloads):
                    if not self.__is_overload(stmt):
                        continue  # skip the impl
            new_body.append(stmt)
        return new_body

    def __parse_generics(self, node: ast.ClassDef):
        new_bases: list[ast.expr] = []
        for base in node.bases:
            if not isinstance(base, ast.Subscript):
                continue
            if isinstance(base.value, ast.Name) and base.value.id == "Generic":
                # This is a generic class
                # We need to extract the type arguments
                if isinstance(base.slice, ast.Tuple):
                    # This is a tuple of types
                    # must remove `ConnectionType` if there
                    generics = [
                        arg.id
                        for arg in base.slice.elts
                        if isinstance(arg, ast.Name)
                        if arg.id != "ConnectionType"
                    ]
                    new_bases.append(
                        ast.Subscript(
                            value=base.value,
                            slice=ast.Tuple(
                                elts=[ast.Name(id=arg) for arg in generics], ctx=ast.Load()
                            ),
                            ctx=ast.Load(),
                        )
                    )
                elif isinstance(base.slice, ast.Name):
                    # This is a single type
                    if base.slice.id == "ConnectionType":
                        # We don't want to include ConnectionType
                        continue
                    new_bases.append(base)
            # if isinstance(base.value, ast.Name) and base.value.id == "_BaseExecutor":
            #     # This is class from collections/queries
            #     return []
        connection_type = ast.Name(id=self.__which_connection_type(), ctx=ast.Load())
        if len(new_bases) == 0:
            # no generics, we need to add the ConnectionType
            slice = connection_type
        else:
            elts: list[ast.expr] = []
            for base in new_bases:
                assert isinstance(base, ast.Subscript)
                slice = base.slice
                assert isinstance(slice, ast.Tuple)
                elts.extend(slice.elts)
            slice = ast.Tuple(elts=[connection_type, *elts], ctx=ast.Load())
        new_bases.append(
            ast.Subscript(
                value=ast.Name(id=node.name, ctx=ast.Load()),
                slice=slice,
                ctx=ast.Load(),
            )
        )
        return new_bases

    def __which_connection_type(self):
        return "ConnectionAsync" if self.colour == "async" else "ConnectionSync"

    def __extract_inner_return_type(self, node: ast.expr | None) -> ast.expr | None:
        # Looking for executor.Result[T]
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "executor"
            and node.value.attr == "Result"
        ):
            # This is executor.Result[...]
            return node.slice  # Return T
        return node  # fallback, return original if not matching

    def visit_FunctionDef(self, node):
        func_def = ast.AsyncFunctionDef if self.colour == "async" else ast.FunctionDef
        new_node = func_def(
            name=node.name,
            args=node.args,
            body=[ast.Expr(value=ast.Constant(value=Ellipsis))],
            decorator_list=node.decorator_list,
            returns=self.__extract_inner_return_type(node.returns),
            type_comment=node.type_comment,
        )
        return ast.copy_location(new_node, node)


from weaviate.collections.aggregations.hybrid import executor as agg_hybrid
from weaviate.collections.aggregations.near_image import executor as agg_near_image
from weaviate.collections.aggregations.near_object import executor as agg_near_object
from weaviate.collections.aggregations.near_text import executor as agg_near_text
from weaviate.collections.aggregations.near_vector import executor as agg_near_vector
from weaviate.collections.aggregations.over_all import executor as agg_over_all
from weaviate.collections.backups import executor as backups
from weaviate.collections.cluster import executor as cluster
from weaviate.collections.config import executor as config
from weaviate.collections.data import executor as data
from weaviate.collections.queries.bm25.generate import executor as generate_bm25
from weaviate.collections.queries.bm25.query import executor as query_bm25
from weaviate.collections.queries.fetch_object_by_id import executor as fetch_object_by_id
from weaviate.collections.queries.fetch_objects.generate import executor as generate_fetch_objects
from weaviate.collections.queries.fetch_objects.query import executor as query_fetch_objects
from weaviate.collections.queries.fetch_objects_by_ids.generate import (
    executor as generate_fetch_objects_by_ids,
)
from weaviate.collections.queries.fetch_objects_by_ids.query import (
    executor as query_fetch_objects_by_ids,
)
from weaviate.collections.queries.hybrid.generate import executor as generate_hybrid
from weaviate.collections.queries.hybrid.query import executor as query_hybrid
from weaviate.collections.queries.near_image.generate import executor as generate_near_image
from weaviate.collections.queries.near_image.query import executor as query_near_image
from weaviate.collections.queries.near_media.generate import executor as generate_near_media
from weaviate.collections.queries.near_media.query import executor as query_near_media
from weaviate.collections.queries.near_object.generate import executor as generate_near_object
from weaviate.collections.queries.near_object.query import executor as query_near_object
from weaviate.collections.queries.near_text.generate import executor as generate_near_text
from weaviate.collections.queries.near_text.query import executor as query_near_text
from weaviate.collections.queries.near_vector.generate import executor as generate_near_vector
from weaviate.collections.queries.near_vector.query import executor as query_near_vector
from weaviate.debug import executor as debug
from weaviate.rbac import executor as rbac
from weaviate.collections.tenants import executor as tenants
from weaviate.users import executor as users

for module in [
    agg_hybrid,
    agg_near_image,
    agg_near_object,
    agg_near_text,
    agg_near_vector,
    agg_over_all,
    backups,
    cluster,
    config,
    data,
    debug,
    generate_bm25,
    generate_fetch_objects,
    generate_fetch_objects_by_ids,
    generate_hybrid,
    generate_near_image,
    generate_near_media,
    generate_near_object,
    generate_near_text,
    generate_near_vector,
    fetch_object_by_id,
    query_bm25,
    query_fetch_objects,
    query_fetch_objects_by_ids,
    query_hybrid,
    query_near_image,
    query_near_media,
    query_near_object,
    query_near_text,
    query_near_vector,
    rbac,
    tenants,
    users,
]:
    source = textwrap.dedent(inspect.getsource(module))

    colours: list[Literal["sync", "async"]] = ["sync", "async"]
    for colour in colours:
        tree = ast.parse(source, mode="exec", type_comments=True)

        transformer = ExecutorTransformer(colour)
        stubbed = transformer.visit(tree)

        imports = [
            node for node in stubbed.body if isinstance(node, (ast.Import, ast.ImportFrom))
        ] + [
            ast.ImportFrom(
                module="weaviate.connect.v4",
                names=[ast.alias(name=f"Connection{colour.capitalize()}", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module=".executor",
                names=[ast.alias(name=name, asname=None) for name in transformer.executor_names],
                level=0,
            ),
        ]
        stubbed.body = imports + [node for node in stubbed.body if isinstance(node, ast.ClassDef)]
        ast.fix_missing_locations(stubbed)

        dir = cast(str, module.__package__).replace(".", "/")
        file = f"{dir}/{colour}.pyi" if colour == "sync" else f"{dir}/{colour}_.pyi"
        with open(file, "w") as f:
            print(f"Writing {file}")
            f.write(ast.unparse(stubbed))
