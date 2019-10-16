import weaviate

w = weaviate.Weaviate("http://localhost:8080")

x = w.get_c11y_vector("Test")
