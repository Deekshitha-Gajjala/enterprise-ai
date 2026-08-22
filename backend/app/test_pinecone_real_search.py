from pinecone_store import search_pinecone


question = "What is this PDF about?"


print()
print("==============================")
print("PINECONE REAL SEARCH TEST")
print("==============================")
print()

results = search_pinecone(
    question,
    top_k=5,
)

print(
    f"Found {len(results)} results."
)

print()

for i, result in enumerate(
    results,
    start=1,
):

    print(
        f"RESULT {i}"
    )

    print(
        "File:",
        result["filename"]
    )

    print(
        "Page:",
        result["page"]
    )

    print(
        "Score:",
        result["score"]
    )

    print(
        "Text:"
    )

    print(
        result["text"]
    )

    print(
        "-" * 60
    )