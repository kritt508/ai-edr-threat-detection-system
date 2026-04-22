# 🛡️ AI-Powered Endpoint Detection & Response (EDR)

## 📌 Overview

This project is an AI-powered Endpoint Detection and Response (EDR) system designed to detect advanced cyber threats using behavior-based analysis and Large Language Models (LLMs).

It integrates malware sandboxing, anomaly detection, and AI-driven threat analysis to improve detection accuracy.

---

## 🚀 Key Features

* 🔍 Malware Behavior Analysis (Sandbox)
* 🧠 AI-based Threat Detection (LLM + RAG)
* 📡 Beaconing Detection (C2 Communication)
* 📊 Risk Scoring System
* ⚙️ Automated Analysis Workflow
* ☁️ Cloud-based Sandbox Environment

---

## 🧱 System Architecture

![Architecture](docs/architecture.png)

Flow:
Upload File → Sandbox → Log Collection → AI Analysis → Threat Report

---

## 🔐 Security Capabilities

* Behavior-based detection
* Anomaly detection
* MITRE ATT&CK mapping
* Threat classification
* Automated incident analysis

---

## 🧩 MITRE ATT&CK Mapping

| Technique | Description                |
| --------- | -------------------------- |
| T1071     | Application Layer Protocol |
| T1055     | Process Injection          |
| T1547     | Persistence                |

---

## 🛠️ Tech Stack

* Backend: Flask / Django
* Frontend: Streamlit
* AI: LLM + RAG
* DevOps: Docker
* Cloud: Azure

---

## 🎥 Demo

(Add your video link here)

---

## ⚙️ Installation

```bash
git clone https://github.com/yourname/ai-edr-threat-detection-system.git
cd ai-edr-threat-detection-system
docker-compose up -d
```

---

## 📊 Example Output

```json
{
  "threat_level": "HIGH",
  "malware_type": "RAT",
  "confidence": 0.94,
  "behavior": ["Beaconing", "Persistence"]
}
```

---

## 📬 Contact

* GitHub: https://github.com/yourname
