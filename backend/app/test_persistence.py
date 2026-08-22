from embeddings import create_embeddings
from vector_store import VectorStore


texts = [
    "Sales planning is one of the first functions in sales management.",
    "Sales forecasting helps organizations estimate future sales.",
    "Sales territories define the geographical areas assigned to salespeople.",
    "Employee attendance records are maintained by the HR department.",
    "The weather forecast predicts rain tomorrow."
]


# Create embeddings
embeddings = create_embeddings(texts)


# Create vector store
store = VectorStore()

store.create_index(embeddings, texts)

print("Index created.")


# Save the index
store.save()

print("Index saved.")


# Create a completely new VectorStore object
new_store = VectorStore()

# Load the saved index
new_store.load()

print("Index loaded.")


# Search
question = "Why is sales planning important?"

question_embedding = create_embeddings([question])

results = new_store.search(
    question_embedding,
    top_k=3
)


print("\nSearch results:")

for i, result in enumerate(results):
    print(f"\n--- Result {i + 1} ---")
    print("Distance:", result["distance"])
    print("Chunk:", result["chunk"])