import pytest as pytest

pytest.skip("Not implemented yet", allow_module_level=True)

# import sys
# from typing import List, Optional

# if sys.version_info < (3, 9):
#     from typing_extensions import Annotated
# else:
#     from typing import Annotated

# from weaviate.collections.classes.config import _PropertyConfig
# from weaviate.collections.classes.orm import BaseProperty, Reference
# from weaviate.types import UUIDS


# class Group(BaseProperty):
#     name: str


# @pytest.mark.parametrize(
#     "member_type,expected",
#     [
#         (str, "text"),
#         (int, "int"),
#         (float, "number"),
#         (List[str], "text[]"),
#         (List[int], "int[]"),
#         (List[float], "number[]"),
#     ],
# )
# @pytest.mark.parametrize("optional", [True, False])
# def test_types(member_type, expected: str, optional: bool):
#     if optional:
#         member_type = Optional[member_type]

#     class ModelTypes(BaseProperty):
#         name: member_type

#     non_optional_types = ModelTypes.type_to_dict(ModelTypes)
#     assert non_optional_types[0]["dataType"][0] == expected


# @pytest.mark.parametrize(
#     "member_type, annotation ,expected",
#     [
#         (str, _PropertyConfig(index_filterable=False), "text"),
#         (UUIDS, Reference(Group), "Group"),
#         (Optional[UUIDS], Reference(Group), "Group"),
#     ],
# )
# def test_types_annotation(member_type, annotation, expected: str):
#     member_type = Annotated[member_type, annotation]

#     class ModelTypes(BaseProperty):
#         name: member_type

#     non_optional_types = ModelTypes.type_to_dict(ModelTypes)
#     assert non_optional_types[0]["dataType"][0] == expected
