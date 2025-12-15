# 🎓 HKU-Mate: Intelligent Course Assistant

**Powered by**

![](https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white)
![](https://img.shields.io/badge/LangChain-1C3C3C.svg?style=for-the-badge&logo=LangChain&logoColor=white)
![](https://img.shields.io/badge/LangGraph-1C3C3C.svg?style=for-the-badge&logo=LangGraph&logoColor=white)
![](https://img.shields.io/badge/Docker-2496ED.svg?style=for-the-badge&logo=Docker&logoColor=white)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent course assistant built with **LangChain DeepAgents** and **LightRAG**, designed for the HKU Data Mining course. The system provides knowledge retrieval, forum post generation, study material creation, and automated Moodle interaction.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [1: Using requirements.txt](#method-1-using-requirementstxt-recommended)
  - [2: Using Docker](#method-2-using-docker)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Team](#-team)

## ✨ Features

### 1. 🔍 Intelligent Knowledge Q&A

- **KB ON Mode**: Retrieves answers from course materials (lectures, slides, past exams) with precise citations
- **KB OFF Mode**: Pure LLM reasoning for open-ended discussions
- Supports multiple retrieval modes: `hybrid`, `local`, `global`, `naive`

### 2. 📝 Forum Post Generation

- Analyzes conversation history automatically
- Extracts "understood parts" and "confusion points"
- Generates structured, professional forum posts
- One-click publish to Moodle via browser automation

### 3. 📚 Study Material Generation

- Creates comprehensive study reports
- Generates cheat sheets with definitions, workflows, and key concepts
- Includes comparison tables and practical examples
- All content includes source citations

### 4. 🌐 Moodle Integration

- Automated browser control via Model Context Protocol (MCP)
- Pre-fills forum forms automatically
- User retains final control for review and submission

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HKU-Mate Course Assistant                    │
│                    (DeepAgents Framework)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐   ┌────────────────────────────────────┐  │
│  │   Main Agent     │   │          4 Sub-Agents              │  │
│  │  (Orchestrator)  │──▶│  • Knowledge Retriever             │  │
│  └──────────────────┘   │  • Forum Composer                  │  │
│                         │  • Moodle Publisher                │  │
│                         │  • Cheat Sheet Generator           │  │
│                         └────────────────────────────────────┘  │
│                                       │                          │
│                                       ▼                          │
│                         ┌────────────────────────────────────┐  │
│                         │           7 Tools                  │  │
│                         │  • lightrag_query                  │  │
│                         │  • get_lecture_content             │  │
│                         │  • search_exam_papers              │  │
│                         │  • generate_forum_draft            │  │
│                         │  • format_forum_post               │  │
│                         │  • generate_study_report           │  │
│                         │  • create_cheat_sheet              │  │
│                         └────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │      LightRAG Server            │
                    │   (Knowledge Graph + RAG)       │
                    │      Docker Container           │
                    └─────────────────────────────────┘
```

### Data Flow

```
User Input → Deep Agents UI (localhost:3000)
                    │
                    ▼
           LangGraph Server (localhost:2024)
                    │
                    ▼
           Course Assistant Agent
                    │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
   Sub-Agents → Tools → LightRAG (localhost:9621)
                    │
                    ▼
           Response with Citations
```

## 📋 Prerequisites

| Requirement             | Version | Purpose                      |
| ----------------------- | ------- | ---------------------------- |
| Python                  | 3.10+   | Runtime environment          |
| Node.js                 | 18+     | Frontend UI                  |
| Docker & Docker Compose | Latest  | LightRAG deployment          |
| Claude API Key          | -       | LLM provider (Anthropic)     |
| Chrome Browser          | Latest  | Moodle automation (optional) |

## 🔧 Installation

### 1: Using requirements.txt (Recommended)

#### Step 1: Clone the Repository

```bash
git clone https://github.com/syyyydszzz/Data_mining.git
cd Data_mining
```

#### Step 2: Create Python Environment

```bash
# Using conda (recommended)
conda create -n course-assistant python=3.11
conda activate course-assistant

# Or using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

#### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Required environment variables:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional - for third-party API proxies
ANTHROPIC_BASE_URL=https://api.anthropic.com

# LightRAG Configuration
LIGHTRAG_BASE_URL=http://localhost:9621
LIGHTRAG_API_KEY=  # Leave empty if not using authentication

# Model Configuration
CLAUDE_MODEL=claude-sonnet-4-20250514
RECURSION_LIMIT=30

# Moodle Integration (optional)
MOODLE_FORUM_URL=https://moodle.hku.hk/mod/forum/view.php?id=YOUR_ID
```

#### Step 5: Start LightRAG with Docker

```bash
# Start LightRAG container
docker-compose up -d

# Verify it's running
curl http://localhost:9621/health
# Or check status
curl http://localhost:9621/documents/pipeline_status
```

#### Step 6: Start the Backend Server

```bash
langgraph dev
# Server runs at http://127.0.0.1:2024
```

#### Step 7: Start the Frontend UI

```bash
cd deep-agents-ui

# Configure frontend (first time only)
cat > .env.local << 'EOF'
NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024"
NEXT_PUBLIC_AGENT_ID=course-assistant
EOF

# Install dependencies and start
npm install
npm run dev
# UI runs at http://localhost:3000
```

### 2: Using Docker to install lightrag

#### Full Docker Deployment

```bash
# Start all services
docker-compose up -d

# Check container status
docker ps
```

The `docker-compose.yml` includes:

- **LightRAG**: Knowledge graph and RAG engine on port 9621
- Volume mounts for persistent data:
  - `./data/rag_storage` - Vector database storage
  - `./data/inputs` - Course materials (PDFs, slides)

## 🚀 Quick Start

### One-Command Start (Recommended)

For systems with Moodle integration:

```bash
./start_with_chrome.sh
```

This script will:

1. ✅ Start MCP-dedicated Chrome browser
2. ⏸️ Wait for you to login to Moodle
3. ✅ Start LangGraph server

### Manual Start

```bash
# Terminal 1: Start LightRAG
docker-compose up -d

# Terminal 2: Start Backend
conda activate course-assistant
langgraph dev

# Terminal 3: Start Frontend
cd deep-agents-ui && npm run dev

# Terminal 4: (Optional) Start Chrome for Moodle
./start_chrome_debug.sh
```

### Verify Installation

```bash
# Check LightRAG
curl http://localhost:9621/documents/pipeline_status

# Check LangGraph Server
curl http://127.0.0.1:2024/ok

# Check Frontend
open http://localhost:3000
```

## 📖 Usage Examples

### Example 1: Knowledge Query (KB ON)

**User Input:**

```
What is the Transformer architecture?
```

*With KB Toggle: ON*

**System Response:**

```
Transformer is a neural network architecture based on the self-attention mechanism[1]. 
It consists of encoder and decoder stacks, each containing multi-head attention layers 
and feed-forward networks[2].

**References:**
[1] Data Mining Lecture 9, Slides 15-18
[2] 2023 Exam, Question 5
```

### Example 2: Open Discussion (KB OFF)

**User Input:**

```
What are the applications of AI in healthcare?
```

*With KB Toggle: OFF*

**System Response:**

```
Answer based on general knowledge (course materials not retrieved):

AI has numerous applications in healthcare:
1. Medical image analysis (X-rays, MRIs)
2. Disease prediction and risk assessment
3. Drug discovery and development
4. Personalized treatment recommendations
...

💡 Tip: Enable KB switch to see course-specific content.
```

### Example 3: Generate Forum Post

**User Input:**

```
Help me generate a forum post about my confusion with RAG architecture
```

**System Response:**

```markdown
# Understanding and Questions about RAG Architecture

## What I Understand
Through our discussion, I understand that:
1. RAG combines retrieval with generation
2. It uses vector similarity for document matching
...

## My Confusion Points
However, I still have questions about:
1. How does the retrieval threshold affect accuracy?
2. What happens when relevant documents aren't found?
...

## AI Assistant Summary
Key points from our discussion:
- RAG architecture consists of three main components...
(Source: Lecture 8, Slides 26-27)
```

### Example 4: Generate Cheat Sheet

**User Input:**

```
Create a cheat sheet for Machine Learning fundamentals
```

**System Response:**
A structured HTML cheat sheet containing:

- Core definitions
- Key formulas
- Common pitfalls
- Use cases
- All with source citations

### Example 5: Post to Moodle Forum

1. Click the **"Post to Forum"** button (turns blue)
2. Enter your forum content
3. Click Send
4. AI fills the Moodle form automatically
5. Review in Chrome and click "Post to forum" to submit

## 📁 Project Structure

```
Data_mining/
├── 📄 Core Files
│   ├── course_assistant.py          # Main agent entry point
│   ├── course_tools.py              # 7 tool functions (RAG, forum, reports)
│   ├── course_subagents.json        # 4 sub-agent configurations
│   ├── course_instructions.md       # System prompts
│   ├── lightrag_client.py           # LightRAG API client
│   ├── state.py                     # State definitions
│   ├── mcp_config.py                # MCP browser configuration
│   ├── mcp_tools.py                 # MCP tool implementations
│   └── moodle_helpers.py            # Moodle interaction helpers
│
├── 📄 Configuration
│   ├── langgraph.json               # LangGraph server config
│   ├── requirements.txt             # Python dependencies
│   ├── docker-compose.yml           # Docker services config
│   └── .env.example                 # Environment template
│
├── 📄 Scripts
│   ├── start_with_chrome.sh         # One-click startup script
│   └── start_chrome_debug.sh        # Chrome debug mode launcher
│
├── 📄 Documentation
│   ├── README.md                    # This file
│   ├── PROJECT_ARCHITECTURE.md      # Detailed architecture docs
│   ├── QUICK_START.md               # Quick start guide
│   ├── POST_TO_FORUM_GUIDE.md       # Forum posting guide
│   └── CLAUDE.md                    # AI assistant guidelines
│
├── 📁 Frontend
│   └── deep-agents-ui/              # Next.js frontend application
│
└── 📁 Data (Docker mounted)
    ├── data/rag_storage/            # LightRAG vector database
    └── data/inputs/                 # Course materials (PDF/PPT)
```

## ⚙️ Configuration

### LangGraph Configuration (`langgraph.json`)

```json
{
  "dependencies": ["."],
  "graphs": {
    "course-assistant": "./course_assistant.py:agent"
  },
  "env": ".env"
}
```

### Docker Configuration (`docker-compose.yml`)

```yaml
services:
  lightrag:
    image: ghcr.io/hkuds/lightrag:latest
    ports:
      - "9621:9621"
    volumes:
      - ./data/rag_storage:/app/data/rag_storage
      - ./data/inputs:/app/data/inputs
```

### Key Dependencies

| Package             | Version | Purpose             |
| ------------------- | ------- | ------------------- |
| langchain           | >=1.0.2 | Core framework      |
| langgraph           | >=0.6.0 | Agent orchestration |
| deepagents          | >=0.2.6 | Agent abstraction   |
| langchain-anthropic | >=1.0.0 | Claude integration  |
| mcp                 | >=1.0.0 | Browser automation  |

## ❓ Troubleshooting

### LightRAG Connection Failed

```bash
# Check Docker container status
docker ps | grep lightrag

# View container logs
docker logs lightrag

# Restart the container
docker-compose restart lightrag
```

### Claude API Error

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test API connection
python -c "from course_assistant import model; print(model.invoke('test').content)"
```

### Frontend Cannot Connect to Backend

1. Verify `.env.local` configuration:

   ```
   NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024"
   ```

2. Ensure backend is running:

   ```bash
   curl http://127.0.0.1:2024/ok
   ```

### MCP/Chrome Connection Issues

```bash
# Check if Chrome is running with debug port
ps aux | grep "remote-debugging-port=9222"

# Kill existing Chrome debug instance
pkill -f 'remote-debugging-port=9222'

# Restart Chrome
./start_chrome_debug.sh
```

### Port Already in Use

```bash
# Find process using port
lsof -i :9621  # LightRAG
lsof -i :2024  # LangGraph
lsof -i :3000  # Frontend
lsof -i :9222  # Chrome debug

# Kill the process
kill -9 <PID>
```

## 👥 Team

|    Name     | University Number |
| :---------: | :---------------: |
| Su Yongyuan |    3036661020     |
|  Ren Liubo  |    3036654675     |
| Chen Zhixin |    3036654053     |
| Xue Chaowei |    3036657536     |
|  Yu Erfei   |    3036657732     |

## 🔗 Links

- **GitHub Repository**: [https://github.com/syyyydszzz/Data_mining.git](https://github.com/syyyydszzz/Data_mining.git)
- **LangChain Documentation**: [https://python.langchain.com/](https://python.langchain.com/)
- **LightRAG Project**: [https://github.com/HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)
- **DeepAgents Framework**: [https://github.com/langchain-ai/deep-agents](https://github.com/langchain-ai/deep-agents)

---



