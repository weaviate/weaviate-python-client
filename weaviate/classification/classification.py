


class Classification:

    def start(self, config):
        pass

    def get_knn_config(self, schema_class_name, k, based_on_properties, classify_properties):

        if not isinstance(schema_class_name, str):
            raise TypeError("Schema class name must be of type string")
        if not isinstance(k, int):
            raise TypeError("K must be of type integer")
        if isinstance(based_on_properties, str):
            based_on_properties = [based_on_properties]
        if isinstance(classify_properties, str):
            classify_properties = [classify_properties]
        if not isinstance(based_on_properties, list):
            raise TypeError("Based on properties must be of type string or list of strings")
        if not isinstance(classify_properties, list):
            raise TypeError("Classify properties must be of type string or list of strings")
        if k <= 0:
            raise ValueError("K must must take a value >= 1")

        config = {
            "class": schema_class_name,
            "k": k,
            "basedOnProperties": based_on_properties,
            "classifyProperties": classify_properties,
            "type": "knn"
        }

        return config

    def get_contextual_config(self):
        pass