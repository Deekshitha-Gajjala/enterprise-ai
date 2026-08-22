from chunker import split_text

text = """
Sales planning is one of the first functions in the process of sales management.
Before undertaking any other managerial function, having a good plan is imperative.
The reality is that certain aspects of planning can be carried over from the prior quarter.
"""

chunks = split_text(text, chunk_size=100, overlap=20)

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)