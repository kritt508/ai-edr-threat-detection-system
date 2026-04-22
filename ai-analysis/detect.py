import os
import json

base_dir = os.path.dirname(__file__)
file_path = os.path.join(base_dir, "..", "logs", "sample-log.json")

with open(file_path) as f:
    data = json.load(f)

if "beaconing" in data["behavior"]:
    print("⚠️ Threat detected: Beaconing activity")
else:
    print("Safe")