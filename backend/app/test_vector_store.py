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


# User's question
question = "Why is sales planning important?"


# Create embedding for the question
question_embedding = create_embeddings([question])


# Search
results = store.search(question_embedding, top_k=3)


print("\nQuestion:")
print(question)

print("\nMost relevant chunks:")

for i, result in enumerate(results):
    print(f"\n--- Result {i + 1} ---")
    print("Distance:", result["distance"])
    print("Chunk:", result["chunk"])