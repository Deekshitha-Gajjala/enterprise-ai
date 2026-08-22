import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec


# Load .env
load_dotenv()


# Get API key
api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise RuntimeError(
        "PINECONE_API_KEY was not found in D:\\7th sem\\.env"
    )


# Connect to Pinecone
pc = Pinecone(
    api_key=api_key
)


# Index name
INDEX_NAME = "enterprise-ai"


# Create index if it does not exist
if not pc.has_index(INDEX_NAME):

    print("Creating Pinecone index...")

    pc.create_index(
        name=INDEX_NAME,
        vector_type="dense",
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",
        ),
        deletion_protection="disabled",
    )

    print("Pinecone index created.")

else:

    print("Pinecone index already exists.")


# Display index information
description = pc.describe_index(
    INDEX_NAME
)

print()
print("====================================")
print("PINECONE INDEX")
print("====================================")
print("Name:", description.name)
print("Dimension:", description.dimension)
print("Metric:", description.metric)
print("Host:", description.host)
print("Status:", description.status)
print("====================================")