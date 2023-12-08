# from typing import List, Optional, Union

# import pytest

# from weaviate.collections.classes.grpc import (
#     PROPERTIES,
#     FromReference,
#     FromReferenceMultiTarget,
# )
# from weaviate.collections.queries.base import _PropertiesParser


# @pytest.mark.skip(reason="string syntax has been temporarily removed from the API")
# @pytest.mark.parametrize(
#     "properties,output",
#     [
#         (["name"], ["name"]),
#         ([FromReference(link_on="name")], [FromReference(link_on="name")]),
#         (["name", FromReference(link_on="name")], ["name", FromReference(link_on="name")]),
#         (
#             [FromReferenceMultiTarget(link_on="name", target_collection="Test"), "name"],
#             ["name", FromReferenceMultiTarget(link_on="name", target_collection="Test")],
#         ),
#         (
#             ["__article__properties__name"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (
#             ["__article__properties__name", "name", "__article__properties__age"],
#             ["name", FromReference(link_on="article", return_properties=["name", "age"])],
#         ),
#         (["__article"], [FromReference(link_on="article")]),
#         (
#             ["__article", "__article__properties__name"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (
#             ["__article__properties__name", "__article"],
#             [FromReference(link_on="article", return_properties=["name"])],
#         ),
#         (None, None),
#         ([None, "name"], ["name"]),
#         (["__article", "name"], ["name", FromReference(link_on="article")]),
#         ("__article", [FromReference(link_on="article")]),
#         ("__article__", [FromReference(link_on="article")]),
#     ],
# )
# def test_properties_parser_success(properties: Optional[PROPERTIES], output: Optional[PROPERTIES]):
#     assert output == _PropertiesParser().parse(properties)


# ERROR_MESSAGE = (
#     lambda s: f"return reference property {s} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
# )


# @pytest.mark.skip(reason="string syntax has been temporarily removed from the API")
# @pytest.mark.parametrize(
#     "wrong",
#     [
#         ["__article__propertie__uuid"],
#         ["__article__propertiess__uuid"],
#         ["__article__metadat__uuid"],
#         ["__article__metadataa__uuid"],
#         "__article__propertie__uuid",
#         "__article__propertiess__uuid",
#         "__article__metadat__uuid",
#         "__article__metadataa__uuid",
#     ],
# )
# def test_properties_parser_error(wrong: Union[str, List[str]]):
#     with pytest.raises(ValueError) as e:
#         out = _PropertiesParser().parse(wrong)
#         print(out)
#     assert e.value.args[0] == ERROR_MESSAGE(wrong[0] if len(wrong) == 1 else wrong)
