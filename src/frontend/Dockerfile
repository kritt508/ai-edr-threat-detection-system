FROM n8nio/n8n:1.77.1

USER root

RUN apk update && apk add --no-cache \
    vim \
    bash \
    python3 \
    py3-pip \
    py3-virtualenv \
    git \
    build-base \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    libpcap-dev \
    tcpdump \
    unzip \
    wget \
    curl \
    ca-certificates \
    jq \
    file-dev

# Virtual env
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    flask flask-cors python-magic requests httpx \
    pefile flare-capa oletools streamlit plotly \
    pandas numpy psycopg2-binary watchdog pydantic \
    langchain langchain-community langchain-google-genai \
    google-generativeai qdrant-client pgvector sqlalchemy \
    maec pyattck mitreattack-python stix2 \
    azure-identity azure-mgmt-compute yara-python scapy

# 🌟 Pre-create folders to prevent errors 
RUN mkdir -p /home/node/.n8n /home/node/azure /home/node/project_malware

WORKDIR /home/node/project_malware

# ลบคำสั่ง USER node ออก เพื่อให้คอนเทนเนอร์นี้ทำงานด้วยสิทธิ์ Root ได้ตลอดรอดฝั่ง