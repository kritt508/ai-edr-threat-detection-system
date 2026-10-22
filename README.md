# Design and Implementation of an Endpoint Security System Using Large Language Models for Cyber Threat Detection and Mitigation

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-Blue%20Team-darkred.svg)](#security-focus)
[![Last Commit](https://img.shields.io/github/last-commit/kritt508/ai-edr-threat-detection-system)](https://github.com/kritt508/ai-edr-threat-detection-system/commits/main)

This project implements an automated endpoint security system for analyzing suspicious Windows and Linux files. It runs samples in Azure sandbox VMs, collects process and network telemetry, then uses Google Gemini with retrieval-augmented generation (RAG) to assess behavior and produce Thai-language reports with MITRE ATT&CK context.

## Evaluation results

The evaluation reported in the Computer Engineering thesis (Nakhon Phanom University, academic year 2025) covered 150 files: 75 Windows samples and 75 Linux samples. The set included 100 malware samples and 50 benign files.

| Measure | Result |
| --- | ---: |
| Overall accuracy | 85.33% |
| Precision | 84.82% |
| Malware recall | 95.00% |
| Windows malware recall | 96.00% |
| Linux malware recall | 94.00% |
| Expert rating for report context | 4.7/5.0 |

Three cybersecurity experts rated the contextual accuracy of the generated reports and Thai recommendations. The sample set included Mirai and Gafgyt Linux malware, a Trojan/stealer, ValleyRAT, Cobalt Strike beacon and sandbox-evasion simulations, and benign system utilities and diagnostic scripts. The APT29 simulation in the reported test set was not detected, so these results should not be read as a guarantee against every threat family or evasion technique.

## Capabilities

- Performs static checks and dynamic analysis on Windows and Linux samples in Azure sandbox VMs.
- Coordinates file handling, VM control, execution, telemetry collection, analysis, and reporting through n8n workflows.
- Collects process and system activity with Procmon on Windows and Strace on Linux, and captures network traffic with TShark.
- Uses Google Gemini and a retrieval-augmented knowledge base to interpret event sequences and map relevant behavior to MITRE ATT&CK.
- Returns a structured risk assessment with behavior summaries and response recommendations in Thai.
- Shuts down and restores the sandbox after analysis to prepare it for another run.

## Workflow

```text
File Upload and Static Checks
      -> n8n Workflow
      -> Azure Sandbox VM Selection and Startup
      -> Sample Execution and Process/Network Monitoring
      -> Log Collection and Filtering
      -> Gemini Analysis with RAG Context
      -> Risk Assessment and Thai-Language Report
      -> Sandbox Shutdown and Restore
```

## Architecture

![System Architecture](docs/System_Architecture.png)

The system connects a Streamlit interface and Flask APIs to n8n workflows, Azure VMs, telemetry tools, Gemini, and a vector knowledge base. Windows and Linux samples are analyzed in separate sandbox environments.

## Previews

### Automated SOAR workflow

![n8n Workflow](docs/n8n_workflow.png)

### Threat analysis dashboard

![Threat Analysis Dashboard](docs/dashboard_main.png)

## Security focus

The system is intended for authorized defensive analysis. Run suspicious files only in an isolated lab that you control. The thesis also reports Azure VM startup delays and less reliable AI summaries when event logs are large or complex.

> For authorized security research, malware-analysis education, and blue-team portfolio use. Never run unknown payloads outside a controlled, isolated lab.

## Tech stack

| Area | Tools |
| --- | --- |
| Backend and API | Python, Flask, Flask-CORS |
| Frontend and Dashboard | Streamlit, Plotly |
| AI Analysis | Google Gemini API, retrieval-augmented generation (RAG) |
| SOAR and Orchestration | n8n |
| Sandbox Infrastructure | Microsoft Azure virtual machines, Docker |
| Endpoint Telemetry | Procmon, Strace |
| Network Telemetry | TShark, PCAP analysis |
| Data Processing | pandas, NumPy |
| Storage and Tracking | Airtable for analysis records, PostgreSQL for n8n |

## Repository structure

```text
src/
  azure/        Azure VM control scripts and API server
  frontend/     Streamlit dashboard, analysis scripts, Docker setup, workflows
  n8n/          Windows and Linux telemetry filtering logic
  vm_linux/     Linux sandbox agent code
  vm_windows/   Windows sandbox agent code
docs/           Architecture and dashboard screenshots
```

## Setup

The project is designed for Linux or WSL-based security workflows.

### 1. Clone the repository

```bash
git clone https://github.com/kritt508/ai-edr-threat-detection-system.git
cd ai-edr-threat-detection-system
```

### 2. Create a Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` from the template:

```bash
cp .env.example .env
```

Replace each placeholder with values for your services. The Docker Compose setup requires the Gemini key, PostgreSQL credentials, an n8n encryption key, and an ngrok token. Azure control scripts also read the service-principal credentials and subscription settings from this file. Keep `.env` private.

### 4. Run the dashboard

```bash
make run
```

This starts the Streamlit interface. The analysis workflow also requires the backend services and Azure sandbox configuration.

### 5. Start the services with Docker Compose

```bash
make docker-up
```

The Compose file mounts `src/azure` and the root `.env` into the containers. Azure VM names and resource groups are configured in `src/azure/vm-control-api.sh`; update them for your Azure environment before using VM controls. Use `make docker-down` to stop the services.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.