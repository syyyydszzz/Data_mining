# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is an **English-language intelligent course assistant** built with **LangChain DeepAgents framework**, integrating LightRAG for knowledge retrieval. The system is designed for English teaching environments and supports dynamic KB (Knowledge Base) toggling with three core functions: Q&A, forum post generation, and study report generation.

**Key Technology**: DeepAgents abstracts away manual LangGraph construction - the entire agent is created with a single `create_deep_agent()` call. All orchestration, tool binding, and subagent routing is handled automatically.

**Language Design**: All user-facing content (agent responses, citations, UI labels, error messages) is in **English**, while code comments remain in Chinese for developer convenience.

---

## Development Commands

### Start Backend (LangGraph Server)
```bash
# Ensure conda environment is activated
conda activate course-assistant

# Install dependencies (first time only)
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL

# Start LangGraph Server (watches for file changes)
langgraph dev
# Server runs at http://127.0.0.1:2024
```

### Start Frontend (Deep Agents UI)
```bash
cd deep-agents-ui

# Configure (first time only)
cat > .env.local << 'EOF'
NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024"
NEXT_PUBLIC_AGENT_ID=course-assistant
EOF

npm install  # First time only
npm run dev
# UI runs at http://localhost:3000
```

### Start LightRAG (Docker)
```bash
docker-compose up -d
# LightRAG API at http://localhost:9621
```

### Test Individual Components
```bash
# Test LightRAG connection
curl http://localhost:9621/documents/pipeline_status

# Test Claude API configuration
python -c "from course_assistant import model; print(model.invoke('test').content)"

# Check agent is properly loaded
curl http://127.0.0.1:2024/ok
```

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Course Assistant                           │
│                   (DeepAgents Framework)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  Main Agent  │  │ 3 Subagents  │  │  7 Tools           │   │
│  │ (English)    │→ │ (English)    │→ │  (English docs)    │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│         ↓                  ↓                    ↓              │
│  course_instructions.md  course_subagents.json  course_tools.py│
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │   LightRAG Client   │
                    │  (lightrag_client.py)│
                    └─────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  LightRAG Server    │
                    │   (Docker HTTP)     │
                    └─────────────────────┘
```

### DeepAgents Pattern

The project uses DeepAgents framework which auto-generates the LangGraph execution graph. You define:
1. **Tools** (`@tool` decorated functions in `course_tools.py`) - English docstrings
2. **Subagents** (JSON config in `course_subagents.json`) - English system prompts
3. **System prompt** (`course_instructions.md`) - English instructions
4. **State** (`state.py`) - Typed state with `kb_enabled` and `current_mode`

Then `create_deep_agent()` automatically creates the full agent with tool calling, subagent routing, and state management.

### Critical Tool Mapping Pattern

**Important**: Subagents in `course_subagents.json` reference tools by **string names**, but DeepAgents requires **actual tool objects**. The `course_assistant.py` has a `TOOL_MAP` that converts tool name strings to tool objects:

```python
TOOL_MAP = {
    "lightrag_query": lightrag_query,
    "get_lecture_content": get_lecture_content,
    "search_exam_papers": search_exam_papers,
    "generate_forum_draft": generate_forum_draft,
    "format_forum_post": format_forum_post,
    "generate_study_report": generate_study_report,
    "create_cheat_sheet": create_cheat_sheet,
}

# Convert tools for each subagent
knowledge_retriever = subagents_config["knowledge_retriever"].copy()
knowledge_retriever["tools"] = [TOOL_MAP[name] for name in knowledge_retriever.get("tools", [])]
```

**When adding new tools**:
1. Define with `@tool` decorator in `course_tools.py` (English docstring)
2. Add to `ALL_TOOLS` list
3. Add to `TOOL_MAP` in `course_assistant.py`
4. Reference by name in `course_subagents.json`
5. Add display config in `deep-agents-ui/src/app/utils/toolDisplayConfig.ts` (English labels)

---

## Core Concepts

### KB Toggle Mechanism (THE MASTER CONTROL)

The **KB (Knowledge Base) toggle** is the central control mechanism:

**Frontend → Backend Flow**:
```
User toggles KB switch
    ↓
Frontend prepends [KB_STATUS:ON] or [KB_STATUS:OFF] to message
    ↓
Main agent reads marker and extracts KB state
    ↓
┌─────────────────────────────────────────────────┐
│ KB ON:  Call RAG tools → Return cited answer   │
│ KB OFF: Pure LLM → Return with disclaimer      │
└─────────────────────────────────────────────────┘
```

**Critical Rules**:
- `[KB_STATUS:ON]`: Use `lightrag_query`, `get_lecture_content`, `search_exam_papers`
- `[KB_STATUS:OFF]`: **NO tool calls allowed**, direct LLM answer with disclaimer:
  ```
  Answer based on general knowledge (course materials not retrieved):
  [content]
  ```

### The Three Subagents (All English Prompts)

#### 1. Knowledge Retriever (`knowledge-retriever`)
**Role**: Search specialist for course materials

**Tools**: `lightrag_query`, `get_lecture_content`, `search_exam_papers`

**Strategy Selection**:
- Concept definitions → `hybrid` mode
- Specific lecture/slide → `local` mode
- Broad topics → `global` mode
- Past exams → `search_exam_papers`

**Output Format**:
```json
{
  "retrieved_content": "RAG architecture contains...",
  "sources": [
    {
      "type": "lecture",
      "lecture_id": 8,
      "slide_range": "26-27",
      "citation": "Data Mining Lecture 8, Slides 26-27"
    }
  ],
  "relevance_explanation": "This explains..."
}
```

#### 2. Forum Composer (`forum-composer`)
**Role**: Conversation analyzer for forum post generation

**Tools**: `generate_forum_draft`, `format_forum_post`

**Analysis Steps**:
1. Identify question evolution
2. Extract "understood parts" (signals: "I understand now...", "I see...")
3. Locate "confusion points" (repeated questions, misunderstandings)
4. Summarize AI response key points

**Output Structure**:
```json
{
  "title": "Understanding and Questions about [Concept]",
  "understood": "Through discussion, I understand that:\n1. ...",
  "confused": "However, I still have questions about:\n1. ...",
  "ai_summary": "Key points:\n- ... (Source: ...)",
  "tags": ["Tag1", "Tag2"]
}
```

#### 3. Study Material Generator (`study-material-generator`)
**Role**: Comprehensive review material creator

**Tools**: `lightrag_query`, `generate_study_report`, `create_cheat_sheet`

**Report Structure**:
- Core concepts (definitions + key components)
- Detailed explanations (workflows, technical details, formulas)
- Examples & applications (from lectures and exams)
- Comparison tables (Method A vs B: advantages, disadvantages, use cases)
- Cheat sheet (core formulas, key steps, common pitfalls)
- Reference sources (properly cited)
- Study recommendations (focus areas, practice problems)

---

## State Management

`state.py` defines `CourseAssistantState` with key fields:

| Field | Type | Purpose |
|-------|------|---------|
| `kb_enabled` | `bool` | **CRITICAL** - Controls RAG tool usage |
| `current_mode` | `str` | "qa" / "forum" / "report" |
| `messages` | `List[Message]` | Auto-managed conversation history |
| `retrieved_documents` | `List[str]` | Cached RAG results |
| `citations` | `List[Dict]` | Source information for answers |
| `conversation_summary` | `str` | For forum generation |
| `user_preferences` | `Dict` | Extensible user settings |

**The agent checks `kb_enabled` at every turn** to decide whether to use RAG tools.

---

## LightRAG Integration

### Client Implementation (`lightrag_client.py`)

Wraps the LightRAG HTTP API with real endpoints:

**Query Endpoint**: `POST /query`

**Query Modes**:
- `"mix"` - Knowledge graph + vector retrieval (recommended) ⭐
- `"hybrid"` - Combines local and global approaches
- `"local"` - Focuses on specific entities and direct relationships
- `"global"` - Analyzes broad patterns in knowledge graph
- `"naive"` - Simple vector similarity search

**Response Format**:
```json
{
  "response": "Generated answer",
  "references": [
    {
      "reference_id": "1",
      "file_path": "lecture_8_slides_26-27.pdf"
    }
  ]
}
```

### Citation Extraction (English Format)

The client parses file paths using regex patterns:

**Lecture Patterns**:
- `lecture_8_slides_26-27.pdf` → `"Lecture 8, Slides 26-27"`
- `Slides-20251022.pdf` → `"Course Slides (2025-10-22)"`
- `lecture_8.pdf` → `"Lecture 8"`

**Exam Patterns**:
- `exam_2023_q5.pdf` → `"2023 Exam, Question 5"`
- `test_2023_5.pdf` → `"2023 Exam, Question 5"`

**Generic Fallback**:
- Any unmatched file → `"Reference Document [ID]: {filename}"`

**Code Example** (`lightrag_client.py:260`):
```python
return {
    "type": "lecture",
    "citation": f"Lecture {lecture_id}, Slides {slide_range}"
}
```

---

## Tool Descriptions (English User-Facing)

All 7 tools have English docstrings and query templates:

### RAG Tools (KB ON only)

#### `lightrag_query(query, mode="mix", ...)`
```python
"""
Query LightRAG knowledge base (core retrieval tool)

Use case: When user message contains [KB_STATUS:ON] marker

Args:
    query: Query question (e.g., "What is RAG architecture?")
    mode: "mix" (recommended) | "hybrid" | "local" | "global" | "naive"

Returns:
    JSON with response, references, and sources
"""
```

#### `get_lecture_content(lecture_id, slide_range)`
```python
"""
Get specific slide content from a lecture

Example: get_lecture_content(8, "26-27")
→ Returns content from Lecture 8, slides 26-27
"""
```

#### `search_exam_papers(topic, year=None)`
```python
"""
Search past exam papers for related questions

Example: search_exam_papers("RAG architecture", "2023")
→ Returns questions about RAG from 2023 exam
"""
```

### Forum Tools

#### `generate_forum_draft(conversation_history)`
Delegates to forum-composer subagent

#### `format_forum_post(draft)`
Formats JSON draft as Markdown with English headers:
```markdown
# {title}

## What I Understand
{understood}

## My Confusion Points
{confused}

## AI Assistant Summary
{ai_summary}
```

### Report Tools

#### `generate_study_report(topic, lectures, include_examples=True)`
Delegates to study-material-generator subagent

#### `create_cheat_sheet(concept)`
Query template: `"Definition, workflow, advantages, challenges, and use cases of {concept}"`

---

## Frontend Integration (English UI)

### Tool Display Config (`deep-agents-ui/src/app/utils/toolDisplayConfig.ts`)

All tool labels are in English:

```typescript
export const TOOL_DISPLAY_CONFIG = {
  lightrag_query: {
    displayName: "Course Material Retrieval",
    pendingMessage: "Retrieving relevant information from lectures and exams...",
    completedMessage: "Retrieval completed",
    icon: "📚"
  },
  // ... other tools
}
```

### UX Optimization: "Assistant is thinking..." Logic

**Smart Display Rules** (`ChatInterface.tsx:481-509`):

The "Assistant is thinking..." indicator is **hidden** when:
1. ✅ Tool calls are executing (status: `pending` or `completed`)
2. ✅ AI message has content output

**Implementation**:
```typescript
const hasActiveToolCalls = processedMessages.some((data) =>
  data.toolCalls.some((tc) => tc.status === "pending" || tc.status === "completed")
);

const hasContentOutput =
  lastMessage?.type === "ai" &&
  extractStringFromMessageContent(lastMessage).trim().length > 0;

// Hide thinking if tools are running or content is streaming
if (hasActiveToolCalls || hasContentOutput) {
  return null;
}
```

**User Experience Flow**:
```
User sends message
    ↓
Show "Assistant is thinking..."
    ↓
┌────────────────────────────────────────┐
│ Tool starts OR content streams         │
│ → "thinking" disappears                │
└────────────────────────────────────────┘
    ↓
Show tool execution status OR AI response
```

### KB Toggle UI (`ChatInterface.tsx:347-349`)

```typescript
const kbStatusLabel = kbEnabled
  ? "KB ON: Use course materials with citations"
  : "KB OFF: Answer with general knowledge only";
```

---

## LangGraph Server Integration

`langgraph.json` specifies the export point:
```json
{
  "graphs": {
    "course-assistant": "./course_assistant.py:agent"
  }
}
```

LangGraph Server automatically:
- ✅ Handles persistence (no manual checkpointer needed)
- ✅ Provides REST API endpoints
- ✅ Manages conversation threads
- ✅ Enables streaming responses

**⚠️ Never add custom checkpointers** - LangGraph Server handles this automatically and will error if you try.

---

## Common Issues & Solutions

### 1. DeepAgents Version Compatibility
- **Requires**: Python 3.11+
- **Field name**: Use `system_prompt` (not `prompt`) in subagent config
- **Checkpointer**: Don't specify when deploying to LangGraph Server

### 2. Tool Registration Issues
If subagent can't access tools:
1. ✅ Tool is in `TOOL_MAP` (`course_assistant.py`)
2. ✅ Tool name in subagent JSON matches key in `TOOL_MAP`
3. ✅ `course_assistant.py` converts string names to objects before passing to `create_deep_agent()`

### 3. LightRAG Connection Errors
If RAG queries fail:
```bash
# 1. Verify Docker container
docker ps | grep lightrag

# 2. Check health endpoint
curl http://localhost:9621/documents/pipeline_status

# 3. Check logs
docker logs <container_id>
```

Error messages are in English:
```json
{
  "error": "Cannot connect to LightRAG service",
  "suggestion": "Please run: cd lightrag && docker-compose up -d"
}
```

### 4. Claude API Configuration
For third-party API proxies:
- Set both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` in `.env`
- URL should include `/v1` suffix if required by proxy
- `course_assistant.py` conditionally adds `base_url` parameter only if set

### 5. Citation Format Issues
All citations must be in **English**:
- ✅ `"Data Mining Lecture 8, Slides 26-27"`
- ✅ `"2023 Exam, Question 3"`
- ❌ `"数据挖掘 第8讲，幻灯片26-27"` (outdated Chinese format)

Check these files if citations are wrong:
- `lightrag_client.py:260` - Citation template
- `course_tools.py:153` - Tool-specific citations
- `course_subagents.json:5` - Subagent output examples

---

## File Change Behavior

LangGraph Server (`langgraph dev`) auto-reloads on file changes:
- ✅ Changes to `.py`, `.json`, `.md` files trigger reload
- ✅ Check terminal for reload messages
- ⚠️ Errors during reload will be logged

**Cache/temp directories** (safe to delete):
- `__pycache__/` - Python bytecode cache
- `.langgraph_api/` - LangGraph runtime state
- `deep-agents-ui/.next/` - Next.js build cache

---

## Quick Reference

### Key Files by Function

| Function | File(s) | Language |
|----------|---------|----------|
| Main agent logic | `course_assistant.py` | Code: Chinese comments, Output: English |
| System instructions | `course_instructions.md` | English |
| Subagent configs | `course_subagents.json` | English system prompts |
| Tool definitions | `course_tools.py` | English docstrings |
| State schema | `state.py` | Chinese comments, English field names |
| RAG client | `lightrag_client.py` | Code: Chinese comments, Citations: English |
| Frontend UI | `deep-agents-ui/src/app/utils/toolDisplayConfig.ts` | English labels |

### Example Citation Formats

**In agent responses**:
```
RAG architecture contains three components[1]. The retriever uses vector search[2].

**References**:
[1] Data Mining Lecture 8, Slides 26-27
[2] 2023 Exam, Question 3
```

**In tool outputs** (`course_tools.py:153`):
```python
"citation": f"Data Mining Lecture {lecture_id}, Slides {slide_range}"
```

**In LightRAG client** (`lightrag_client.py:260`):
```python
"citation": f"Lecture {lecture_id}, Slides {slide_range}"
```

### Example Query Templates

**In `get_lecture_content`**:
```python
query = f"Content of Lecture {lecture_id}, Slides {slide_range}"
```

**In `search_exam_papers`**:
```python
query = f"Past exam questions about {topic}"
if year:
    query += f" (year {year})"
```

**In `create_cheat_sheet`**:
```python
query = f"Definition, workflow, advantages, challenges, and use cases of {concept}"
```

---

## Development Workflow

### Adding a New Feature

1. **Define the tool** (`course_tools.py`):
   ```python
   @tool
   def my_new_tool(param: str) -> str:
       """English docstring"""
       # Implementation
   ```

2. **Add to TOOL_MAP** (`course_assistant.py`):
   ```python
   TOOL_MAP = {
       # ... existing tools
       "my_new_tool": my_new_tool,
   }
   ```

3. **Update subagent config** (`course_subagents.json`):
   ```json
   {
     "my_subagent": {
       "tools": ["my_new_tool"]
     }
   }
   ```

4. **Add frontend display** (`toolDisplayConfig.ts`):
   ```typescript
   my_new_tool: {
     displayName: "My New Feature",
     pendingMessage: "Processing...",
     icon: "🔧"
   }
   ```

5. **Test the integration**:
   ```bash
   # Backend reloads automatically
   langgraph dev

   # Frontend may need restart
   cd deep-agents-ui && npm run dev
   ```

### Debugging Tips

**Backend logs**:
```bash
# Watch LangGraph server logs
langgraph dev
# Look for [TOOL] and [LightRAG] prefixed messages
```

**Frontend logs**:
```bash
# Browser console
# Look for tool call messages and state updates
```

**Test tool directly**:
```python
from course_tools import lightrag_query
result = lightrag_query("What is RAG?", mode="hybrid")
print(result)
```

---

## English Content Checklist

When adding new features, ensure all user-facing content is in **English**:

- [ ] Tool docstrings (`course_tools.py`)
- [ ] Subagent system prompts (`course_subagents.json`)
- [ ] Query templates in tools
- [ ] Citation format strings
- [ ] Error messages and suggestions
- [ ] Frontend tool display names (`toolDisplayConfig.ts`)
- [ ] UI labels and status messages
- [ ] Agent response templates (`course_instructions.md`)

**Code comments can remain in Chinese** for developer convenience.
