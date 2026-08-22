from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


model = SentenceTransformer("all-MiniLM-L6-v2")


texts = [
    "Sales planning is important for managing a sales team.",
    "Planning helps sales managers organize their activities.",
    "The weather is hot today."
]


embeddings = model.encode(texts)

similarity_matrix = cosine_similarity(embeddings)

print("Similarity Matrix:")
print(similarity_matrix)

print("\nText 1 vs Text 2:")
print(similarity_matrix[0][1])

print("\nText 1 vs Text 3:")
print(similarity_matrix[0][2])