import json
import os
import argparse
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import FakeEmbeddings 
# NOTE: In a production environment, use OpenAIEmbeddings or HuggingFace. For resource efficiency and testing purposes, we use Fake/Fast Embeddings. Replace this if an API key is available.

from langchain.docstore.document import Document
from qdrant_client import QdrantClient

# Configure Qdrant connection (based on the service name in Docker Compose)
QDRANT_HOST = "qdrant" 
QDRANT_PORT = 6333
COLLECTION_NAME = "mitre_knowledge_base"

def main():
    print(f"🚀 Starting ingestion into Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")

    # 1. Read data file
    file_path = '/home/node/project_malware/data/mitre_ttp_index.json'
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📄 Loaded {len(data)} TTP records.")

    # 2. Convert data to LangChain Documents
    documents = []
    for item in data:
        # Content for AI reading and retrieval
        page_content = f"Technique: {item['name']} (ID: {item['id']})\nDescription: {item['description']}\nTactics: {', '.join(item['tactics'])}"
        
        # Metadata
        metadata = {
            "id": item['id'],
            "name": item['name'],
            "source": "MITRE ATT&CK"
        }
        documents.append(Document(page_content=page_content, metadata=metadata))

    # 3. Generate Embeddings and store in Qdrant
    # Use FakeEmbeddings for rapid testing (vector size = 768, standard for most models)
    embeddings = FakeEmbeddings(size=768) 
    
    try:
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        qdrant = Qdrant.from_documents(
            documents,
            embeddings,
            url=url,
            prefer_grpc=False,
            collection_name=COLLECTION_NAME,
            force_recreate=True # Recreate collection on every run
        )
        print(f"✅ Successfully ingested {len(documents)} documents into collection '{COLLECTION_NAME}'")
        print("🎉 Knowledge Base is ready for RAG!")
        
    except Exception as e:
        print(f"❌ Failed to ingest data: {e}")

if __name__ == "__main__":
    main()