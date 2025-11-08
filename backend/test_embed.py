from sentence_transformers import SentenceTransformer
print("Loading model all-MiniLM-L6-v2 ...")
m = SentenceTransformer("all-MiniLM-L6-v2")
v = m.encode("test", convert_to_numpy=True)
print("OK — vector length:", len(v))
