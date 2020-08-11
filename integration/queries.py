import weaviate
from weaviate.connect import REST_METHOD_POST


def things_of_result(gql_result):
     return gql_result['data']['Get']['Things']

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

gql_get_sophie_scholl = """
{
  Get {
    Things {
      Person (where: {
        path: ["uuid"]
        operator: Equal
        valueString: "594b7827-f795-40d0-aabb-5e0553953dad"
      }){
        name
        uuid
      }
    }
  }
}
"""

def get_query_for_group(name):
    return ("""
    {
      Get {
        Things {
          Group (where: {
            path: ["name"]
            operator: Equal
            valueString: "%s"
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
    """ % name)

