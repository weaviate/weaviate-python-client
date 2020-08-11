import weaviate
import json
import time

# Setup a client for your local weaviate
client = weaviate.Client("http://localhost:8080")
client.schema.create("https://raw.githubusercontent.com/semi-technologies/weaviate-python-client/master/documentation/getting_started/news-publications.json")

# Create an entity from the Publication class
hq = {
    "name": "The New York Times",
    "headquartersGeoLocation": {
        "latitude": 40.7561454,
        "longitude": -73.9903298
    }
}
client.data_object.create(hq, "Publication", "2db436b5-0557-5016-9c5f-531412adf9c6")

# Create an Author
client.data_object.create({"name": "Jason Bailey"}, "Author", "b36268d4-a6b5-5274-985f-45f13ce0c642")
client.data_object.create({"name": "Alexander Burns"}, "Author", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
# Let weaviate create the uuid
matt_id = client.data_object.create({"name": "Matt Flegenheimer"}, "Author")
print(f"UUID of Matt Flegenheimer: {matt_id}")

# Create an Action
cite_id = client.data_object.create({}, "Cite", semantic_type=weaviate.SEMANTIC_TYPE_ACTIONS)

# Create an Article
article = {
    "title": "Who’s Running for President in 2020?",
    "url": "https://www.nytimes.com/interactive/2019/us/politics/2020-presidential-candidates.html",
    "summary": "Former Vice President Joseph R. Biden Jr. is the presumptive Democratic nominee ...",
    # Reference the publication on creation
    "inPublication": [weaviate.util.generate_local_beacon("2db436b5-0557-5016-9c5f-531412adf9c6")]
}
client.data_object.create(article, "Article", "d412133d-75fc-4ad5-aaae-46465522f1c2")
article = {
    "title": "The 50 Best Movies on Netflix Right Now",
    "url": "https://www.nytimes.com/interactive/2020/arts/television/best-movies-on-netflix.html",
    "summary": "The sheer volume of films on Netflix — and the site’s less than ...",
    "inPublication": [weaviate.util.generate_local_beacon("2db436b5-0557-5016-9c5f-531412adf9c6")]
}
client.data_object.create(article, "Article", "23b9e00c-884c-4543-b68a-abf875c950c4")

time.sleep(2.0)

# Add a reference from the article to the authors
client.data_object.reference.add("d412133d-75fc-4ad5-aaae-46465522f1c2", "hasAuthors", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
client.data_object.reference.add("d412133d-75fc-4ad5-aaae-46465522f1c2", "hasAuthors", matt_id)
client.data_object.reference.add("23b9e00c-884c-4543-b68a-abf875c950c4", "hasAuthors", "b36268d4-a6b5-5274-985f-45f13ce0c642")
# Add a reference from an action type to a thing type
client.data_object.reference.add(cite_id, "citation", "23b9e00c-884c-4543-b68a-abf875c950c4", from_semantic_type=weaviate.SEMANTIC_TYPE_ACTIONS)

# Query the insterted data
gql_get_articles = """
{
  Get {
    Things {
      Article {
        title
        HasAuthors {
          ... on Author {
            name
          }
        }
        InPublication {
          ... on Publication {
            name
          }
        }
        OfCategory {
          ... on Category {
            name
          }
        }
      }
    }
  }
}
"""
query_result = client.query.raw(gql_get_articles)
print("\nQuery results for articles:")
print(json.dumps(query_result, indent=4, sort_keys=True))

# Lets create two categories for classification
client.data_object.create({"name": "entertainment"}, "Category")
client.data_object.create({"name": "politics"}, "Category")

# Give weaviate 2 seconds to update the index with the newly added categories
time.sleep(2.0)

classification_cfg = client.classification.get_contextual_config("Article", "summary", "ofCategory")
classification_status = client.classification.start_and_wait(classification_cfg)
print("\nClassification status:")
print(json.dumps(classification_status, indent=4, sort_keys=True))

query_result = client.query.raw(gql_get_articles)
print("\nQuery results for articles after classification:")
print(json.dumps(query_result, indent=4, sort_keys=True))


