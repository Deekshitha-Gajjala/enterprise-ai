import os

from dotenv import load_dotenv
from pinecone import Pinecone


# Load .env
load_dotenv()


# Get API key
api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise ValueError(
        "PINECONE_API_KEY not found in .env"
    )


# Connect to Pinecone
pc = Pinecone(
    api_key=api_key
)


# Connect to EXISTING index
index = pc.Index(
    "enterprise-ai"
)


print()
print("==============================")
print("PINECONE CONNECTION SUCCESS")
print("==============================")
print()

print("Index name:")
print("enterprise-ai")

print()

print("Index statistics:")

stats = index.describe_index_stats()

print(stats)

print()
print("Connection is working!")