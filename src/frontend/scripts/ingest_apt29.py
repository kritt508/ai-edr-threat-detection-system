import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

# เชื่อมต่อ Qdrant (ใช้ชื่อ service ใน docker)
client = QdrantClient(host="qdrant", port=6333)
model = SentenceTransformer('all-MiniLM-L6-v2')

# สร้าง Collection
client.recreate_collection(
    collection_name="apt29_knowledge",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# ข้อมูลตัวอย่างเทคนิคของ APT29 (คุณสามารถหาเพิ่มจาก MITRE ATT&CK)
data = [
    {"tech": "T1059.001", "desc": "PowerShell: APT29 uses obfuscated PowerShell scripts for initial execution."},
    {"tech": "T1574.002", "desc": "DLL Side-Loading: Placing a malicious DLL in the same directory as a legitimate executable."},
    {"tech": "T1548.002", "desc": "Bypass User Account Control: Elevating privileges using scheduled tasks."}
]

# แปลงเป็น Vector และเก็บใน Qdrant
for i, item in enumerate(data):
    vector = model.encode(item['desc']).tolist()
    client.upsert(
        collection_name="apt29_knowledge",
        points=[{"id": i, "vector": vector, "payload": item}]
    )
print("APT29 Knowledge Base Updated!")