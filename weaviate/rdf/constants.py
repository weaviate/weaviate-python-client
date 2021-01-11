"""
Triple schema as constant.
"""

triple_schema = {
  "classes": [
    {
      "class": "Subject",
      "description": "Subject",
      "properties": [
        {
          "name": "value",
          "description": "value of subject",
          "dataType": [
            "text"
          ],
        },
        {
          "name": "valueKey",
          "description": "valueKey of subject",
          "dataType": [
            "string"
          ],
        }
      ]
    },
    {
      "class": "Predicate",
      "description": "predicate",
      "properties": [
        {
          "name": "value",
          "description": "value",
          "dataType": [
            "text"
          ],
        },
        {
          "name": "valueKey",
          "description": "valueKey",
          "dataType": [
            "string"
          ],
        }
      ]
    },
    {
      "class": "Object",
      "description": "object",
      "properties": [
        {
          "name": "value",
          "description": "value",
          "dataType": [
            "text"
          ],
        },
        {
          "name": "valueKey",
          "description": "valueKey of subject",
          "dataType": [
            "string"
          ],
        }
      ]
    },
    {
      "class": "Triple",
      "description": "rdf triple",
      "properties": [
        {
          "name": "subject",
          "description": "subject of the triple",
          "dataType": [
            "Subject"
          ],
        },
        {
          "name": "predicate",
          "description": "predicate of the triple",
          "dataType": [
            "Predicate"
          ],
        },
        {
          "name": "object",
          "description": "object of the triple",
          "dataType": [
            "Object"
          ],
        }
      ]
    }
  ]
}
