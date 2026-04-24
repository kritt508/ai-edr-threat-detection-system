import json
import os
import argparse
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import FakeEmbeddings 
# หมายเหตุ: ใน Production จริงควรใช้ OpenAIEmbeddings หรือ HuggingFace แต่เพื่อประหยัด Resource และทดสอบระบบ เราจะใช้ Fake/Fast Embedding ไปก่อน หรือถ้าคุณมี API Key ให้เปลี่ยนตรงนี้

from langchain.docstore.document import Document
from qdrant_client import QdrantClient

# ตั้งค่าการเชื่อมต่อ Qdrant (ตามชื่อ Service ใน Docker Compose)
QDRANT_HOST = "qdrant" 
QDRANT_PORT = 6333
COLLECTION_NAME = "mitre_knowledge_base"

def main():
    print(f"🚀 Starting ingestion into Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")

    # 1. อ่านไฟล์ข้อมูล
    file_path = '/home/node/project_malware/data/mitre_ttp_index.json'
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📄 Loaded {len(data)} TTP records.")

    # 2. แปลงข้อมูลเป็น LangChain Documents
    documents = []
    for item in data:
        # เนื้อหาที่จะให้ AI อ่านและค้นหา (Content)
        page_content = f"Technique: {item['name']} (ID: {item['id']})\nDescription: {item['description']}\nTactics: {', '.join(item['tactics'])}"
        
        # ข้อมูลกำกับ (Metadata)
        metadata = {
            "id": item['id'],
            "name": item['name'],
            "source": "MITRE ATT&CK"
        }
        documents.append(Document(page_content=page_content, metadata=metadata))

    # 3. สร้าง Embeddings และบันทึกลง Qdrant
    # ใช้ FakeEmbeddings เพื่อความรวดเร็วในการทดสอบ (ขนาด vector = 768 เท่ากับ model ทั่วไป)
    embeddings = FakeEmbeddings(size=768) 
    
    try:
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        qdrant = Qdrant.from_documents(
            documents,
            embeddings,
            url=url,
            prefer_grpc=False,
            collection_name=COLLECTION_NAME,
            force_recreate=True # สร้างใหม่ทุกครั้งที่รัน
        )
        print(f"✅ Successfully ingested {len(documents)} documents into collection '{COLLECTION_NAME}'")
        print("🎉 Knowledge Base is ready for RAG!")
        
    except Exception as e:
        print(f"❌ Failed to ingest data: {e}")

if __name__ == "__main__":
    main()