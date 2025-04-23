import ast
import importlib
import inspect
import os
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


for subdir, dirs, files in os.walk("./weaviate"):
    for file in files:
        if file != "executor.py":
            continue
        if "connect" in subdir:
            # ignore weaviate/connect/executor.py file
            continue
        if "collections/collections" in subdir:
            # ignore weaviate/collections/collections directory
            continue

        mod = os.path.join(subdir, file)
        mod = mod[2:]  # remove the leading dot and slash
        mod = mod[:-3]  # remove the .py
        mod = mod.replace("/", ".")  # convert into pythonic import

        module = importlib.import_module(mod)
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
                    names=[
                        ast.alias(name=name, asname=None) for name in transformer.executor_names
                    ],
                    level=0,
                ),
            ]
            stubbed.body = imports + [
                node for node in stubbed.body if isinstance(node, ast.ClassDef)
            ]
            ast.fix_missing_locations(stubbed)

            dir = cast(str, module.__package__).replace(".", "/")
            file = f"{dir}/{colour}.pyi" if colour == "sync" else f"{dir}/{colour}_.pyi"
            with open(file, "w") as f:
                print(f"Writing {file}")
                f.write(ast.unparse(stubbed))
