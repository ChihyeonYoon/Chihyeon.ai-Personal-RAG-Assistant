import os
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader

DATA_DIR = "../data"
print(f"Loading from {DATA_DIR}")

# Try loading with DirectoryLoader but without multithreading to see errors
try:
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.pdf",
        loader_cls=UnstructuredFileLoader,
        show_progress=True,
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} documents.")
except Exception as e:
    print(f"Error loading: {e}")
