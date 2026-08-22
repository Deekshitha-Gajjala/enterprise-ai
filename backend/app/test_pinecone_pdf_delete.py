from pinecone_store import delete_pdf_vectors


FILENAME = "Module_1_DL_1.pdf"


print()
print("==============================")
print("PINECONE PDF DELETE TEST")
print("==============================")
print()

print(
    "Deleting vectors for:",
    FILENAME
)

delete_pdf_vectors(
    FILENAME
)

print()
print("Delete request completed.")