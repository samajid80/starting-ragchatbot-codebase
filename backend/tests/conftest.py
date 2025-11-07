"""
Pytest fixtures and mocks for RAG chatbot testing.
Provides mock components to isolate unit tests.
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Course, CourseChunk, Lesson, Source
from vector_store import SearchResults

# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_course():
    """Sample course object for testing"""
    return Course(
        title="Introduction to MCP Servers",
        course_link="https://example.com/mcp",
        instructor="John Doe",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Getting Started",
                lesson_link="https://example.com/mcp/lesson1",
            ),
            Lesson(
                lesson_number=2,
                title="Advanced Features",
                lesson_link="https://example.com/mcp/lesson2",
            ),
            Lesson(
                lesson_number=3,
                title="Best Practices",
                lesson_link="https://example.com/mcp/lesson3",
            ),
        ],
    )


@pytest.fixture
def sample_chunks():
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 1 content: This is the introduction to MCP servers.",
            course_title="Introduction to MCP Servers",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="This lesson covers the basics of MCP protocol.",
            course_title="Introduction to MCP Servers",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Lesson 2 content: Advanced MCP features include context sharing.",
            course_title="Introduction to MCP Servers",
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_search_results():
    """Sample successful search results"""
    return SearchResults(
        documents=[
            "This is the introduction to MCP servers.",
            "MCP protocol allows AI to access external tools.",
        ],
        metadata=[
            {
                "course_title": "Introduction to MCP Servers",
                "lesson_number": 1,
                "chunk_index": 0,
            },
            {
                "course_title": "Introduction to MCP Servers",
                "lesson_number": 1,
                "chunk_index": 1,
            },
        ],
        distances=[0.15, 0.23],
    )


@pytest.fixture
def empty_search_results():
    """Sample empty search results"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Sample error search results"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="No course found matching 'Nonexistent Course'",
    )


# ============================================================================
# MOCK VECTOR STORE FIXTURES
# ============================================================================


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mock VectorStore with predefined behavior"""
    mock_store = Mock()

    # Default search behavior
    mock_store.search.return_value = sample_search_results

    # Mock course name resolution
    mock_store._resolve_course_name.return_value = "Introduction to MCP Servers"

    # Mock lesson link retrieval
    mock_store.get_lesson_link.return_value = "https://example.com/mcp/lesson1"

    # Mock catalog operations
    mock_store.get_existing_course_titles.return_value = ["Introduction to MCP Servers"]
    mock_store.get_course_count.return_value = 1

    return mock_store


@pytest.fixture
def mock_vector_store_empty():
    """Mock VectorStore that returns empty results"""
    mock_store = Mock()

    empty_results = SearchResults(documents=[], metadata=[], distances=[])
    mock_store.search.return_value = empty_results
    mock_store._resolve_course_name.return_value = "Introduction to MCP Servers"
    mock_store.get_lesson_link.return_value = None

    return mock_store


@pytest.fixture
def mock_vector_store_error():
    """Mock VectorStore that returns error results"""
    mock_store = Mock()

    error_results = SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="No course found matching 'Nonexistent Course'",
    )
    mock_store.search.return_value = error_results
    mock_store._resolve_course_name.return_value = None

    return mock_store


# ============================================================================
# MOCK CLAUDE API CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def mock_claude_response_no_tool():
    """Mock Claude API response without tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    # Create mock content with text
    mock_content = Mock()
    mock_content.text = "This is a general knowledge answer that doesn't require searching course content."
    mock_response.content = [mock_content]

    return mock_response


@pytest.fixture
def mock_claude_response_with_tool():
    """Mock Claude API response with tool use request"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Create mock tool use block
    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "search_course_content"
    mock_tool_use.id = "tool_use_123"
    mock_tool_use.input = {
        "query": "What is MCP?",
        "course_name": "Introduction to MCP Servers",
    }

    mock_response.content = [mock_tool_use]

    return mock_response


@pytest.fixture
def mock_claude_final_response():
    """Mock Claude API final response after tool execution"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    mock_content = Mock()
    mock_content.text = "MCP (Model Context Protocol) is a protocol that allows AI to access external tools and data sources."
    mock_response.content = [mock_content]

    return mock_response


@pytest.fixture
def mock_claude_client(mock_claude_response_no_tool, mock_claude_final_response):
    """Mock Anthropic Claude client"""
    mock_client = Mock()

    # Default behavior: return response without tool use
    mock_client.messages.create.return_value = mock_claude_response_no_tool

    return mock_client


@pytest.fixture
def mock_claude_client_with_tools(
    mock_claude_response_with_tool, mock_claude_final_response
):
    """Mock Claude client that uses tools"""
    mock_client = Mock()

    # First call: tool use request
    # Second call: final response
    mock_client.messages.create.side_effect = [
        mock_claude_response_with_tool,
        mock_claude_final_response,
    ]

    return mock_client


# ============================================================================
# MOCK TOOL MANAGER FIXTURES
# ============================================================================


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager with predefined behavior"""
    mock_manager = Mock()

    # Mock tool definitions
    mock_manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "course_name": {"type": "string"},
                    "lesson_number": {"type": "integer"},
                },
                "required": ["query"],
            },
        }
    ]

    # Mock tool execution
    mock_manager.execute_tool.return_value = "[Introduction to MCP Servers - Lesson 1]\nThis is the introduction to MCP servers."

    # Mock sources
    mock_manager.get_last_sources.return_value = [
        Source(
            title="Introduction to MCP Servers - Lesson 1",
            url="https://example.com/mcp/lesson1",
        )
    ]

    mock_manager.reset_sources.return_value = None

    return mock_manager


# ============================================================================
# MOCK SESSION MANAGER FIXTURES
# ============================================================================


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager"""
    mock_manager = Mock()

    # Mock session creation
    mock_manager.create_session.return_value = "session_1"

    # Mock conversation history
    mock_manager.get_conversation_history.return_value = (
        "User: Previous question\nAssistant: Previous answer"
    )

    # Mock add exchange
    mock_manager.add_exchange.return_value = None

    return mock_manager


# ============================================================================
# MOCK CONFIG FIXTURE
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"

    return config


# ============================================================================
# FASTAPI TESTING FIXTURES
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API testing"""
    mock_rag = Mock()

    # Mock session manager
    mock_session_manager = Mock()
    mock_session_manager.create_session.return_value = "session_1"
    mock_rag.session_manager = mock_session_manager

    # Mock query method
    mock_rag.query.return_value = (
        "MCP (Model Context Protocol) is a protocol that allows AI to access external tools.",
        [Source(title="Introduction to MCP Servers - Lesson 1", url="https://example.com/mcp/lesson1")]
    )

    # Mock analytics method
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["Introduction to MCP Servers"]
    }

    return mock_rag


@pytest.fixture
def test_client(mock_rag_system):
    """FastAPI TestClient with mocked RAG system"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    # Import models from the app
    from models import Source

    # Create a test app without static file mounting to avoid import issues
    test_app = FastAPI(title="Test RAG System")

    # Define request/response models inline
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define test endpoints
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/")
    async def root():
        return {"message": "RAG System API"}

    return TestClient(test_app)
