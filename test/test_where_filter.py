"""Unit tests for the GraphQL `Where` filter string rendering.

These do not require a running Weaviate instance; they pin the exact GraphQL
fragments produced client-side.
"""

from weaviate.gql.filter import Where


def test_boolean_list_is_rendered_as_lowercase_graphql_literals() -> None:
    """A boolean list must render as lowercase GraphQL booleans.

    Regression: booleans in a list were rendered with Python's ``str()`` which
    emits ``True``/``False`` (capitalized). That is not a valid GraphQL boolean
    literal and made the whole aggregate query fail to parse server-side,
    whereas a single boolean value was already rendered correctly.
    """
    for value_type in ["valueBooleanArray", "valueBooleanList"]:
        where = Where(
            {
                "operator": "ContainsAny",
                "path": ["active"],
                value_type: [True, False, True],
            }
        )
        rendered = str(where)
        assert "[true,false,true]" in rendered, rendered
        assert "True" not in rendered and "False" not in rendered, rendered


def test_single_boolean_rendering_is_unchanged() -> None:
    where = Where({"operator": "Equal", "path": ["active"], "valueBoolean": True})
    assert "valueBoolean: true" in str(where)

    where = Where({"operator": "Equal", "path": ["active"], "valueBoolean": False})
    assert "valueBoolean: false" in str(where)


def test_other_lists_rendering_is_unchanged() -> None:
    string_list = Where(
        {
            "operator": "ContainsAny",
            "path": ["name"],
            "valueStringArray": ["a", "b"],
        }
    )
    assert 'valueString: ["a","b"]' in str(string_list)

    int_list = Where(
        {
            "operator": "ContainsAny",
            "path": ["count"],
            "valueIntArray": [1, 2],
        }
    )
    assert "valueInt: [1, 2]" in str(int_list)
