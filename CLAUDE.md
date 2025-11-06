# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot for course materials using **tool-based search** with Anthropic's Claude. Unlike traditional RAG systems that always retrieve before generating, this system gives Claude a `search_course_content` tool that it can optionally invoke based on the query type.

**Tech Stack:** FastAPI + ChromaDB + Claude Sonnet 4 + Sentence Transformers + Vanilla JS frontend

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Create .env file with your Anthropic API key
ANTHROPIC_API_KEY=your_key_here
```

### Running
```bash
# Option 1: Quick start from root
./run.sh

# Option 2: Manual start from root
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Access:** Web UI at http://localhost:8000, API docs at http://localhost:8000/docs

### Testing
No test suite currently exists. The codebase has no pytest configuration or test files.

## Architecture

### Key Design Decision: Tool-Based RAG (Not Traditional RAG)

This system uses Anthropic's tool-calling capabilities rather than automatically retrieving before every generation:

```
Query → Claude decides → Use search tool OR answer from knowledge
         ↓ (if tool needed)
      search_course_content tool
         ↓
      Vector search results
         ↓
      Claude synthesizes final response
```

**Why this matters:**
- General knowledge questions don't trigger unnecessary searches
- Claude has agency to decide when retrieval is needed
- System prompt limits to "one search per query maximum"
- More efficient and contextually appropriate than always retrieving

### Component Flow

**RAGSystem** (`rag_system.py`) - Main orchestrator
- Entry point for all queries and document operations
- Coordinates: DocumentProcessor → VectorStore → AIGenerator → SessionManager
- Manages ToolManager with CourseSearchTool registration

**VectorStore** (`vector_store.py`) - Two ChromaDB collections pattern
- `course_catalog`: Stores course metadata (title, instructor, lessons as JSON)
- `course_content`: Stores chunked lesson content with embeddings

**Why two collections?**
1. Semantic search for course name matching ("MCP" → "MCP: Build Rich-Context AI Apps")
2. Filtered content search within specific courses/lessons
3. Separation of catalog discovery from content retrieval

**AIGenerator** (`ai_generator.py`) - Claude API wrapper
- System prompt instructs: use tool only for course-specific questions
- Temperature 0, max tokens 800
- Handles tool execution loop: initial response → execute tool → final response

**DocumentProcessor** (`document_processor.py`) - Course file parser
- Expected format: Line 1 = title, Line 2 = link, Line 3 = instructor
- Extracts lessons using regex: `Lesson \d+: .+`
- Chunks with overlap (800 chars, 100 overlap) at sentence boundaries
- Adds lesson context to chunks for better embeddings

**SessionManager** (`session_manager.py`) - In-memory conversation history
- Simple counter-based IDs: `session_1`, `session_2`, etc.
- Keeps last 2 exchanges (4 messages) per session
- **Ephemeral**: Lost on server restart

### Data Flow Patterns

**Document Ingestion:**
```
.txt file → DocumentProcessor.process_course_document()
          → Course object + CourseChunk[]
          → add_course_metadata() → course_catalog collection
          → add_course_content() → course_content collection
```

**Query Processing:**
```
User query → RAGSystem.query()
           → AIGenerator with tool definitions
           → Claude evaluates query
           → (optional) CourseSearchTool.execute()
           → VectorStore.search(query, course_name?, lesson_number?)
           → Formatted results → Claude
           → Final response + sources
           → SessionManager.add_exchange()
```

### Important Non-Obvious Behaviors

1. **Session Storage is Ephemeral**
   - Sessions only exist in memory during server runtime
   - Restarting uvicorn loses all conversation history
   - No persistence to disk or database

2. **Course Deduplication on Folder Load**
   - `add_course_folder()` checks existing titles before processing
   - Uses course title (not filename) as unique identifier
   - Skips re-processing but doesn't update existing courses
   - Set `clear_existing=True` to rebuild from scratch

3. **Lesson Context Injection in Chunks**
   - First chunk of lesson: `"Lesson {N} content: {chunk}"`
   - Last chunk of course: `"Course {title} Lesson {N} content: {chunk}"`
   - Improves semantic meaning of embeddings for lesson-specific queries

4. **Tool Execution is Single-Pass**
   - Claude gets ONE opportunity to use the search tool per query
   - Tool results are sent back as user message
   - Claude then generates final response (no second tool use)
   - Multiple tool calls in one response execute in batch

5. **Course Name Matching is Fuzzy**
   - Uses semantic vector search on course titles
   - Partial matches work: "MCP" finds "Introduction to MCP Servers"
   - Returns best match (top 1 result from catalog)
   - Lesson filtering is exact integer match

6. **ChromaDB Filter Behavior**
   - Filters use `where` clause (applied during search, not after)
   - Combined filters use `$and` operator
   - Empty filter (None) searches all content

7. **Source Tracking via Tool Manager**
   - `CourseSearchTool` stores sources in `self.last_sources`
   - `ToolManager.get_last_sources()` retrieves them after query
   - Sources reset after each retrieval to avoid stale data
   - Format: `["Course Title - Lesson N", ...]`

## Configuration

All settings in `backend/config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `ANTHROPIC_MODEL` | claude-sonnet-4-20250514 | Claude model version |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | SentenceTransformer model |
| `CHUNK_SIZE` | 800 | Characters per chunk |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |
| `MAX_RESULTS` | 5 | Top K search results |
| `MAX_HISTORY` | 2 | Conversation exchanges to keep |
| `CHROMA_PATH` | ./chroma_db | Vector DB storage location |

**Environment:** Only `ANTHROPIC_API_KEY` required in `.env`

## File Structure

```
backend/
├── app.py                  # FastAPI endpoints, startup event loads docs
├── rag_system.py          # Main orchestrator
├── vector_store.py        # ChromaDB with dual-collection pattern
├── ai_generator.py        # Claude API with tool execution loop
├── document_processor.py  # Course file parser and chunker
├── search_tools.py        # CourseSearchTool + ToolManager
├── session_manager.py     # In-memory conversation history
├── config.py              # Centralized configuration
└── models.py              # Pydantic data models

frontend/
├── index.html             # Chat interface
├── script.js              # API calls, session mgmt, markdown rendering
└── style.css              # Styling

docs/                      # Course material files (.txt, .pdf, .docx)
```

## Common Workflows

### Adding New Course Documents
Place files in `docs/` folder. On next server restart, `app.py` startup event auto-loads them via `rag_system.add_course_folder()`. Files must follow format:
```
Line 1: Course Title
Line 2: https://course-link.com
Line 3: Instructor Name
...rest of content with "Lesson N: Title" markers...
```

### Modifying Search Behavior
- **Change result count:** Modify `MAX_RESULTS` in `config.py`
- **Adjust chunking:** Modify `CHUNK_SIZE` or `CHUNK_OVERLAP` in `config.py`
- **Change tool instructions:** Edit system prompt in `ai_generator.py` line 8-30
- **Add filters:** Extend `vector_store.py` `_build_filter()` method

### Changing Claude's Behavior
System prompt in `AIGenerator.SYSTEM_PROMPT` (line 8-30 of `ai_generator.py`) controls:
- When to use search tool vs general knowledge
- Response format and tone
- Tool usage limits (currently "one search per query maximum")

### Frontend Customization
- **Suggested questions:** Edit `index.html` `.suggested-item` elements
- **Welcome message:** Modify `script.js` line 152
- **Markdown rendering:** Uses `marked.js` from CDN (line 120 of `script.js`)

## API Endpoints

**POST /api/query**
- Input: `{query: str, session_id?: str}`
- Output: `{answer: str, sources: str[], session_id: str}`
- Creates new session if `session_id` not provided

**GET /api/courses**
- Output: `{total_courses: int, course_titles: str[]}`
- Returns catalog statistics from ChromaDB

## Gotchas

1. **Static File Caching:** Custom `DevStaticFiles` class adds no-cache headers. Frontend also uses cache-busting query params (`script.js?v=9`).

2. **Resource Tracker Warnings:** Suppressed at app.py line 1-2. These are benign ChromaDB multiprocessing warnings.

3. **ChromaDB Persistence:** Data persists in `./chroma_db` directory. Delete this folder to reset vector store.

4. **Session IDs are Sequential:** Simple counter pattern. Not suitable for production (no UUID, no authentication).

5. **No Input Validation:** Query length, course names, and lesson numbers not validated before processing.

6. **Embedding Model Download:** First run downloads all-MiniLM-L6-v2 (~80MB) to cache. May take time on slow connections.
- always use uv to run the server do not use pip directly
- make sure to use uv to manage all dependencies
- use uv to run python files