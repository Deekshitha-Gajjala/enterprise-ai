from embeddings import create_embeddings


texts = [
    "Sales planning is important for managing a sales team.",
    "Planning helps sales managers organize their activities.",
    "The weather is hot today."
]

embeddings = create_embeddings(texts)

for i, embedding in enumerate(embeddings):
    print(f"\nText {i + 1}")
    print("Vector dimensions:", len(embedding))
    print("First 10 values:", embedding[:10])