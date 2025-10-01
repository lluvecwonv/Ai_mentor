# JBNU AI Mentor

An AI-powered academic mentoring system for Jeonbuk National University students, providing personalized curriculum recommendations, course information, and academic guidance.

<p align="center">
  <img src="./Ai_mentor.png" alt="AI Mentor Interface" width="600"/>
</p>

## System Architecture

The system consists of multiple microservices:
- **Frontend**: Open WebUI interface (Port 5173)
- **Backend**: API server (Port 8080)
- **Pipeline**: Request routing and processing (Port 9099)
- **AI Modules**: Specialized services for different tasks

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js and npm
- Conda (recommended)
- OpenAI API Key
- PostgreSQL database

### 1. Frontend Setup (Port 5173)
```bash
cd open-webui
npm install
npm run dev
```

### 2. Backend Setup (Port 8080)
```bash
conda create --name open-webui python=3.11
conda activate open-webui
cd open-webui/backend/
pip install -r requirements.txt -U
sh dev.sh
```

### 3. Pipeline Setup (Port 9099)
```bash
conda activate open-webui
cd pipelines/
pip install -r requirements.txt
./start.sh
```

### 4. AI Modules Setup

Each module requires environment configuration in `.env` file:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DB_HOST`: Database host
- `DB_PASSWORD`: Database password

```bash
conda activate open-webui

# LLM Agent (Port 8001) - Main orchestration service
cd ai_modules/llm_agent-main/
uvicorn main:app --host 0.0.0.0 --port 8001

# Curriculum Service (Port 7996) - Course recommendation and graph generation
cd ai_modules/curriculum-main/
python main.py

# FAISS Search (Port 7997) - Vector-based course search
cd ai_modules/faiss_search-main/
python main.py

# Tool Dumb (Port 7998) - Department mapping service
cd ai_modules/tool_dumb-main/
python main.py

# Tool SQL (Port 7999) - Database query service
cd ai_modules/tool_sql-main/
python main.py
```

## Initial Configuration

### Pipeline Connection
Navigate to **Admin Panel** > **Settings** > **Connections** > **OpenAI API Management**
- URL: `http://localhost:9099`
- API Key: `0p3n-w3bu!`

### Upload Pipeline
Go to **Admin Panel** > **Settings** > **Pipeline** and upload the required pipeline configuration.

### Task Model Configuration
Set **External Task Model** or **Local Task Model** to **OpenAI Pipeline** in Settings.

## Features

- Personalized curriculum recommendations with visual graph
- Course search and information retrieval
- Professor and department information queries
- Conversation context management
- Multi-agent query routing system

## Technology Stack

- **Frontend**: Svelte, Open WebUI
- **Backend**: Python, FastAPI, LangGraph
- **AI**: OpenAI GPT, LangChain
- **Database**: PostgreSQL
- **Search**: FAISS vector database
- **Visualization**: NetworkX, Matplotlib

## License

This project is developed for academic purposes at Jeonbuk National University.
