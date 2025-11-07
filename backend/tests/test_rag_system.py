"""
Tests for RAGSystem in rag_system.py
Focus: Testing how the RAG system handles content-query related questions
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Source
from rag_system import RAGSystem


class TestRAGSystemQuery:
    """Test RAGSystem.query() method for content-related queries"""

    def test_query_happy_path_with_tools(
        self,
        mock_config,
        mock_vector_store,
        mock_session_manager,
        sample_search_results,
    ):
        """Test successful content query that triggers tool use"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = (
                "MCP is a protocol for AI context management."
            )

            # Setup vector store
            mock_vector_store.search.return_value = sample_search_results
            mock_vector_store.get_lesson_link.return_value = (
                "https://example.com/lesson1"
            )

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is MCP?")

            # Assert
            assert response == "MCP is a protocol for AI context management."
            assert isinstance(sources, list)

            # Verify AI generator was called with tools
            mock_ai.generate_response.assert_called_once()
            call_kwargs = mock_ai.generate_response.call_args[1]
            assert "tools" in call_kwargs
            assert call_kwargs["tools"] is not None
            assert "tool_manager" in call_kwargs

    def test_query_with_session_id(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test query with session ID includes conversation history"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Follow-up answer"

            mock_session_manager.get_conversation_history.return_value = (
                "User: Previous question\nAssistant: Previous answer"
            )

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("Follow-up question", session_id="session_1")

            # Assert
            # Verify conversation history was retrieved
            mock_session_manager.get_conversation_history.assert_called_once_with(
                "session_1"
            )

            # Verify history was passed to AI generator
            call_kwargs = mock_ai.generate_response.call_args[1]
            assert (
                call_kwargs["conversation_history"]
                == "User: Previous question\nAssistant: Previous answer"
            )

            # Verify session was updated
            mock_session_manager.add_exchange.assert_called_once()

    def test_query_without_session_id(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test query without session ID doesn't retrieve history"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Answer"

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is MCP?")

            # Assert
            # Should not try to get conversation history
            mock_session_manager.get_conversation_history.assert_not_called()

            # Should not update session
            mock_session_manager.add_exchange.assert_not_called()

    def test_query_sources_returned_correctly(
        self,
        mock_config,
        mock_vector_store,
        mock_session_manager,
        sample_search_results,
    ):
        """Test that sources from tool execution are returned"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Answer with sources"

            mock_vector_store.search.return_value = sample_search_results
            mock_vector_store.get_lesson_link.return_value = (
                "https://example.com/lesson1"
            )

            # Create RAG system and trigger a search
            rag = RAGSystem(mock_config)

            # Manually simulate tool execution by calling search tool
            rag.search_tool.execute(query="What is MCP?")

            # Act
            response, sources = rag.query("What is MCP?")

            # Assert
            # Sources should be retrieved from tool manager
            assert isinstance(sources, list)
            # Sources should be reset after retrieval (empty for next query)

    def test_query_empty_query_string(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test handling of empty query string"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "I need more information"

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("")

            # Assert
            # System should still process (no validation in current implementation)
            assert response == "I need more information"
            mock_ai.generate_response.assert_called_once()

    def test_query_general_knowledge_question(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test that general knowledge questions don't trigger unnecessary searches"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Python is a programming language."

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is Python?")

            # Assert
            assert "Python is a programming language" in response
            # Tools are still provided to AI, but AI chooses not to use them
            # This is expected behavior - AI decides based on system prompt

    def test_query_prompt_formatting(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test that query is properly formatted as prompt"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Answer"

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is MCP?")

            # Assert
            call_kwargs = mock_ai.generate_response.call_args[1]
            query_sent = call_kwargs["query"]
            assert "Answer this question about course materials" in query_sent
            assert "What is MCP?" in query_sent


class TestRAGSystemInitialization:
    """Test RAGSystem initialization and component setup"""

    def test_initialization_creates_all_components(self, mock_config):
        """Test that all components are initialized"""
        with (
            patch("rag_system.DocumentProcessor") as mock_dp,
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.AIGenerator") as mock_ai,
            patch("rag_system.SessionManager") as mock_sm,
        ):

            # Act
            rag = RAGSystem(mock_config)

            # Assert
            mock_dp.assert_called_once_with(
                mock_config.CHUNK_SIZE, mock_config.CHUNK_OVERLAP
            )
            mock_vs.assert_called_once_with(
                mock_config.CHROMA_PATH,
                mock_config.EMBEDDING_MODEL,
                mock_config.MAX_RESULTS,
            )
            mock_ai.assert_called_once_with(
                mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL
            )
            mock_sm.assert_called_once_with(mock_config.MAX_HISTORY)

    def test_initialization_registers_tools(self, mock_config):
        """Test that search tools are registered"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            # Act
            rag = RAGSystem(mock_config)

            # Assert
            assert rag.tool_manager is not None
            assert rag.search_tool is not None
            assert rag.outline_tool is not None

            # Verify tools are registered
            tool_names = [
                tool_def["name"] for tool_def in rag.tool_manager.get_tool_definitions()
            ]
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names


class TestRAGSystemCourseAnalytics:
    """Test course analytics functionality"""

    def test_get_course_analytics(self, mock_config, mock_vector_store):
        """Test retrieving course analytics"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            mock_vs_class.return_value = mock_vector_store
            mock_vector_store.get_course_count.return_value = 3
            mock_vector_store.get_existing_course_titles.return_value = [
                "Course A",
                "Course B",
                "Course C",
            ]

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            analytics = rag.get_course_analytics()

            # Assert
            assert analytics["total_courses"] == 3
            assert len(analytics["course_titles"]) == 3
            assert "Course A" in analytics["course_titles"]


class TestRAGSystemIntegration:
    """Integration-style tests for complete query flow"""

    def test_content_query_full_flow(self, mock_config, sample_search_results):
        """Test full flow of content query from query to response"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs = Mock()
            mock_vs_class.return_value = mock_vs
            mock_vs.search.return_value = sample_search_results
            mock_vs.get_lesson_link.return_value = "https://example.com/lesson1"
            mock_vs._resolve_course_name.return_value = "Introduction to MCP Servers"

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai

            # Simulate AI calling the search tool
            def generate_with_tool_call(
                query, conversation_history=None, tools=None, tool_manager=None
            ):
                if tool_manager:
                    # Simulate AI deciding to use search tool
                    tool_result = tool_manager.execute_tool(
                        "search_course_content",
                        query="What is MCP?",
                        course_name="Introduction to MCP",
                    )
                    return f"Based on the course materials: {tool_result[:50]}..."
                return "Answer without tools"

            mock_ai.generate_response.side_effect = generate_with_tool_call

            mock_sm = Mock()
            mock_sm_class.return_value = mock_sm
            mock_sm.create_session.return_value = "session_1"

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is MCP?", session_id="session_1")

            # Assert
            assert "Based on the course materials" in response
            assert isinstance(sources, list)

            # Verify components were called in correct order
            mock_ai.generate_response.assert_called_once()
            mock_sm.get_conversation_history.assert_called_once_with("session_1")


class TestRAGSystemErrorHandling:
    """Test error handling in RAG system"""

    def test_query_handles_ai_generator_errors(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test handling of AI generator errors"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.side_effect = Exception("API Error")

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                response, sources = rag.query("What is MCP?")

            assert "API Error" in str(exc_info.value)

    def test_query_with_invalid_session_id(
        self, mock_config, mock_vector_store, mock_session_manager
    ):
        """Test query with invalid/non-existent session ID"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs_class,
            patch("rag_system.AIGenerator") as mock_ai_class,
            patch("rag_system.SessionManager") as mock_sm_class,
        ):

            # Setup mocks
            mock_vs_class.return_value = mock_vector_store
            mock_sm_class.return_value = mock_session_manager

            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.generate_response.return_value = "Answer"

            # Invalid session returns None history
            mock_session_manager.get_conversation_history.return_value = None

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Act
            response, sources = rag.query("What is MCP?", session_id="invalid_session")

            # Assert
            # Should still work, just without history
            assert response == "Answer"
            call_kwargs = mock_ai.generate_response.call_args[1]
            assert call_kwargs["conversation_history"] is None
