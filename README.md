# JBNU AI Mentor

An AI-powered academic mentoring system for Jeonbuk National University students, providing personalized curriculum recommendations, course information, and academic guidance.

<p align="center">
  <img src="./Ai_mentor.png" alt="AI Mentor Interface" width="600"/>
</p>

## System Architecture

The system consists of multiple microservices communicating via HTTP APIs:
- **Open WebUI**: Web interface (Port 8080)
- **Pipeline**: Request routing and processing (Port 9099)
- **AI Modules**: Specialized microservices for different tasks

## Project Structure

```
AiMentor_edit/
├── open-webui/                  # Web UI application (Port 8080)
├── pipelines/                   # Request routing pipeline (Port 9099)
├── ai_modules/                  # AI microservices
│   ├── llm_agent-main/          # Main orchestration service with LangGraph (Port 8001)
│   ├── curriculum-main/         # Course recommendation and graph generation (Port 7996)
│   ├── faiss_search-main/       # Vector-based course search (Port 7997)
│   ├── department_mapping-main/ # Department mapping service (Port 8000)
│   └── tool_sql-main/           # Database query service (Port 7999)
├── docker-compose.yml           # Docker orchestration configuration
├── restart_all.sh               # Service restart script
└── Ai_mentor.png                # System interface screenshot
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Access the application at `http://localhost:8080`

### Live Demo

🌐 **Production Service**: [http://210.117.181.110:8080](http://210.117.181.110:8080)

### Manual Setup

#### Prerequisites
- Python 3.11+
- OpenAI API Key
- PostgreSQL database

#### Environment Configuration

Create `.env` file with:
```bash
OPENAI_API_KEY=your_openai_api_key
DB_HOST=your_database_host
DB_PASSWORD=your_database_password
VECTOR_DB_PASSWORD=your_vector_db_password
```

#### Starting Services

```bash
# Open WebUI (Port 8080)
cd open-webui
docker run -d -p 8080:8080 --name openwebui [image]

# Pipeline (Port 9099)
cd pipelines/
pip install -r requirements.txt
./start.sh

# LLM Agent (Port 8001)
cd ai_modules/llm_agent-main/
uvicorn main:app --host 0.0.0.0 --port 8001

# Curriculum Service (Port 7996)
cd ai_modules/curriculum-main/
python main.py

# FAISS Search (Port 7997)
cd ai_modules/faiss_search-main/
python main.py

# Department Mapping (Port 8000)
cd ai_modules/department_mapping-main/
python main.py

# SQL Tool (Port 7999)
cd ai_modules/tool_sql-main/
python main.py
```

## Features

- Personalized curriculum recommendations with visual graph
- Course search and information retrieval
- Professor and department information queries
- Conversation context management
- Multi-agent query routing system
- Light query validation for academic-focused responses

## Technology Stack

- **Frontend**: Svelte, Open WebUI
- **Backend**: Python, FastAPI, LangGraph
- **AI**: OpenAI GPT, LangChain
- **Database**: PostgreSQL
- **Search**: FAISS vector database
- **Visualization**: NetworkX, Matplotlib
- **Containerization**: Docker, Docker Compose

## License

This project is developed for academic purposes at Jeonbuk National University.

## Copyright

All rights reserved by [Natural Language Learning Lab (NLL Lab)](https://sites.google.com/view/nlllab/main), Jeonbuk National University.

© 2024 NLL Lab, JBNU. All rights reserved.
