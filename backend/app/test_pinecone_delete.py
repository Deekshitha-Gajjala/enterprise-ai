import os

from dotenv import load_dotenv
from pinecone import Pinecone


load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise ValueError("PINECONE_API_KEY not found in .env")


pc = Pinecone(api_key=api_key)

index = pc.Index("enterprise-ai")


# Delete our test vector
index.delete(
    ids=["test-vector-1"]
)


print()
print("==============================")
print("TEST VECTOR DELETED")
print("==============================")
print()


stats = index.describe_index_stats()

print(stats)