import os

from dotenv import load_dotenv
from pinecone import Pinecone


load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise ValueError(
        "PINECONE_API_KEY not found in .env"
    )


# Connect to Pinecone
pc = Pinecone(
    api_key=api_key
)

# Connect to existing index
index = pc.Index(
    "enterprise-ai"
)


# Test vector
vector = [0.0] * 384

# Make one value non-zero
vector[0] = 1.0


# Insert test record
index.upsert(
    vectors=[
        {
            "id": "test-vector-1",
            "values": vector,
            "metadata": {
                "text": "This is a Pinecone test record.",
                "filename": "test.txt",
                "page": 1,
            },
        }
    ]
)


print()
print("==============================")
print("VECTOR INSERTED SUCCESSFULLY")
print("==============================")
print()


# Check statistics
stats = index.describe_index_stats()

print(stats)