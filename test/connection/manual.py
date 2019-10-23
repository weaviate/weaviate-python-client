import weaviate

w = weaviate.Client("http://localhost:8080")

x = w.get_c11y_vector("Test")
