import weaviate
from weaviate.connect import REST_METHOD_POST


def query_data(gql_query):
    connection = weaviate.connect.Connection(url="http://localhost:8080", auth_client_secret="")
    return connection.run_rest("/graphql", REST_METHOD_POST, {"query": gql_query}).json()['data']['Get']['Things']

gql_get_group_legends = """
{
  Get {
    Things {
      Group (where: {
        path: ["name"]
        operator: Equal
        valueString: "Legends"
      }) {
        name
        uuid
        Members {
          ... on Person {
            name
            uuid
          }
        }
      }
    }
  }
}
"""

gql_get_group_chemists = """
{
  Get {
    Things {
      Group (where: {
        path: ["name"]
        operator: Equal
        valueString: "Chemists"
      }) {
        name
        uuid
        Members {
          ... on Person {
            name
            uuid
          }
        }
      }
    }
  }
}
"""