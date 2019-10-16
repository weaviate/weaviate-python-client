import weaviate

print("Weaviate should be running at local host 8080")
w = weaviate.Weaviate("http://localhost:8080")

print("Checking if weaviate is reachable")
if not w.is_reachable():
    exit(1)



print("Integration test successfully completed")
exit(0)
