tripple_schema = {
  "things": {
    "type": "thing",
    "name": "rdf-triples",
    "classes": [
      {
        "class": "Subject",
        "description": "Subject",
        "keywords": [],
        "properties": [
          {
            "name": "value",
            "description": "value of subject",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "valueKey",
            "description": "valueKey of subject",
            "dataType": [
              "string"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      },
      {
        "class": "Predicate",
        "description": "predicate",
        "keywords": [],
        "properties": [
          {
            "name": "value",
            "description": "value",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "valueKey",
            "description": "valueKey",
            "dataType": [
              "string"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      },
      {
        "class": "Object",
        "description": "object",
        "keywords": [],
        "properties": [
          {
            "name": "value",
            "description": "value",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "valueKey",
            "description": "valueKey of subject",
            "dataType": [
              "string"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      },
      {
        "class": "Triple",
        "description": "rdf triple",
        "keywords": [],
        "properties": [
          {
            "name": "subject",
            "description": "subject of the triple",
            "dataType": [
              "Subject"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "predicate",
            "description": "predicate of the triple",
            "dataType": [
              "Predicate"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "object",
            "description": "object of the triple",
            "dataType": [
              "Object"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      }
    ]
  }
}