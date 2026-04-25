import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Connect to Qdrant (using the service name defined in Docker)
client = QdrantClient(host="qdrant", port=6333)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create Collection
client.recreate_collection(
    collection_name="apt29_knowledge",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# Sample data for APT29 techniques (refer to MITRE ATT&CK for more)
data = [
    {"tech": "T1059.001", "desc": "PowerShell: APT29 uses obfuscated PowerShell scripts for initial execution."},
    {"tech": "T1574.002", "desc": "DLL Side-Loading: Placing a malicious DLL in the same directory as a legitimate executable."},
    {"tech": "T1548.002", "desc": "Bypass User Account Control: Elevating privileges using scheduled tasks."}
]

# Convert to Vectors and store in Qdrant
for i, item in enumerate(data):
    vector = model.encode(item['desc']).tolist()
    client.upsert(
        collection_name="apt29_knowledge",
        points=[{"id": i, "vector": vector, "payload": item}]
    )
print("APT29 Knowledge Base Updated!")