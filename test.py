import os
from pinecone import Pinecone, ServerlessSpec

api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)
index = pc.Index("mathtutor-e5-large")

# Check stats
stats = index.describe_index_stats()
print("dddd", stats)
