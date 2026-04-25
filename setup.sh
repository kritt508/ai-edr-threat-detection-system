#!/bin/bash

# AI-EDR Setup Script for Linux/WSL
# This script automates the installation of dependencies and environment setup.

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️ Starting AI-EDR System Setup...${NC}"

# 1. Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}Error: python3 is not installed. Please install it first.${NC}"
    exit 1
fi

# 2. Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo -e "${RED}Warning: Docker is not installed. Containerized deployment will not be available.${NC}"
fi

# 3. Create Virtual Environment
echo -e "${GREEN}Creating Python Virtual Environment (venv)...${NC}"
python3 -m venv venv
source venv/bin/activate

# 4. Install Dependencies
echo -e "${GREEN}Installing Python dependencies from requirements.txt...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 5. Prepare Environment Variables
if [ ! -f .env ]; then
    echo -e "${GREEN}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${BLUE}Please update the .env file with your API keys.${NC}"
else
    echo -e "${BLUE}.env file already exists. Skipping...${NC}"
fi

# 6. Final message
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${BLUE}To activate the environment, run: ${NC}source venv/bin/activate"
echo -e "${BLUE}To run the app, use: ${NC}python src/main.py (or use 'make run' if Makefile is present)"
