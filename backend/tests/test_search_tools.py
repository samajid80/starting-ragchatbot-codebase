"""
Tests for CourseSearchTool in search_tools.py
Focus: Testing the execute() method with various scenarios
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Source
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method"""

    def test_execute_happy_path_no_filters(
        self, mock_vector_store, sample_search_results
    ):
        """Test successful search without course or lesson filters"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Act
        result = tool.execute(query="What is MCP?")

        # Assert
        assert result is not None
        assert isinstance(result, str)
        assert "Introduction to MCP Servers" in result
        assert "This is the introduction" in result
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=None
        )

    def test_execute_happy_path_with_course_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test successful search with course name filter"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Act
        result = tool.execute(query="What is MCP?", course_name="Introduction to MCP")

        # Assert
        assert result is not None
        assert "Introduction to MCP Servers" in result
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=None
        )

    def test_execute_happy_path_with_lesson_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test successful search with lesson number filter"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Act
        result = tool.execute(query="What is MCP?", lesson_number=1)

        # Assert
        assert result is not None
        assert "Lesson 1" in result
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=1
        )

    def test_execute_happy_path_with_both_filters(
        self, mock_vector_store, sample_search_results
    ):
        """Test successful search with both course and lesson filters"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Act
        result = tool.execute(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=1
        )

        # Assert
        assert result is not None
        assert "Introduction to MCP Servers" in result
        assert "Lesson 1" in result
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=1
        )

    def test_execute_error_course_not_found(self, mock_vector_store_error):
        """Test handling of course not found error"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store_error)

        # Act
        result = tool.execute(query="What is MCP?", course_name="Nonexistent Course")

        # Assert
        assert result is not None
        assert "No course found matching 'Nonexistent Course'" in result

    def test_execute_error_empty_results(self, mock_vector_store_empty):
        """Test handling of empty search results"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store_empty)

        # Act
        result = tool.execute(query="Unknown topic")

        # Assert
        assert result is not None
        assert "No relevant content found" in result

    def test_execute_error_empty_results_with_course_filter(
        self, mock_vector_store_empty
    ):
        """Test empty results message includes course name when filtered"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store_empty)

        # Act
        result = tool.execute(query="Unknown topic", course_name="Introduction to MCP")

        # Assert
        assert result is not None
        assert "No relevant content found" in result
        assert "Introduction to MCP" in result

    def test_execute_error_empty_results_with_lesson_filter(
        self, mock_vector_store_empty
    ):
        """Test empty results message includes lesson number when filtered"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store_empty)

        # Act
        result = tool.execute(query="Unknown topic", lesson_number=5)

        # Assert
        assert result is not None
        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_execute_source_tracking(self, mock_vector_store, sample_search_results):
        """Test that sources are correctly tracked after search"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )

        # Act
        result = tool.execute(query="What is MCP?")

        # Assert
        assert result is not None
        assert len(tool.last_sources) == 2  # Two search results = two sources
        assert all(isinstance(source, Source) for source in tool.last_sources)
        assert tool.last_sources[0].title == "Introduction to MCP Servers - Lesson 1"
        assert tool.last_sources[0].url == "https://example.com/mcp/lesson1"

    def test_execute_source_tracking_without_lesson_link(
        self, mock_vector_store, sample_search_results
    ):
        """Test source tracking when lesson link is not available"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None

        # Act
        result = tool.execute(query="What is MCP?")

        # Assert
        assert result is not None
        assert len(tool.last_sources) == 2
        assert tool.last_sources[0].url is None

    def test_execute_with_invalid_lesson_number_type(self, mock_vector_store):
        """Test handling of invalid lesson number (negative or zero)"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)

        # Note: This tests the current behavior, which may allow 0 or negative numbers
        # In a production system, you'd want validation to reject these
        # Act
        result = tool.execute(query="What is MCP?", lesson_number=0)

        # Assert
        # Currently, the code doesn't validate lesson_number
        # This test documents the current behavior
        mock_vector_store.search.assert_called_once()


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool(self, mock_vector_store):
        """Test registering a tool"""
        # Arrange
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        # Act
        manager.register_tool(tool)

        # Assert
        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test retrieving all tool definitions"""
        # Arrange
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Act
        definitions = manager.get_tool_definitions()

        # Assert
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        assert "description" in definitions[0]
        assert "input_schema" in definitions[0]

    def test_execute_tool_success(self, mock_vector_store, sample_search_results):
        """Test successful tool execution via manager"""
        # Arrange
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results

        # Act
        result = manager.execute_tool("search_course_content", query="What is MCP?")

        # Assert
        assert result is not None
        assert isinstance(result, str)
        assert "Introduction to MCP Servers" in result

    def test_execute_tool_not_found(self, mock_vector_store):
        """Test executing a non-existent tool"""
        # Arrange
        manager = ToolManager()

        # Act
        result = manager.execute_tool("nonexistent_tool", query="test")

        # Assert
        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources from last search"""
        # Arrange
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )

        # Execute a search to generate sources
        manager.execute_tool("search_course_content", query="What is MCP?")

        # Act
        sources = manager.get_last_sources()

        # Assert
        assert len(sources) == 2
        assert all(isinstance(source, Source) for source in sources)

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources after retrieval"""
        # Arrange
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )

        # Execute a search to generate sources
        manager.execute_tool("search_course_content", query="What is MCP?")

        # Act
        manager.reset_sources()
        sources_after_reset = manager.get_last_sources()

        # Assert
        assert len(sources_after_reset) == 0


class TestCourseSearchToolFormatResults:
    """Test _format_results() internal method behavior"""

    def test_format_results_structure(self, mock_vector_store, sample_search_results):
        """Test that results are formatted correctly"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )

        # Act
        result = tool.execute(query="What is MCP?")

        # Assert
        # Check formatting structure
        assert "[Introduction to MCP Servers - Lesson 1]" in result
        assert "\n\n" in result  # Results should be separated by double newlines

    def test_format_results_multiple_documents(self, mock_vector_store):
        """Test formatting with multiple search results"""
        # Arrange
        tool = CourseSearchTool(mock_vector_store)
        multi_results = SearchResults(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
                {"course_title": "Course B", "lesson_number": 1},
            ],
            distances=[0.1, 0.2, 0.3],
        )
        mock_vector_store.search.return_value = multi_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson"

        # Act
        result = tool.execute(query="Test query")

        # Assert
        assert "[Course A - Lesson 1]" in result
        assert "[Course A - Lesson 2]" in result
        assert "[Course B - Lesson 1]" in result
        assert "Doc 1" in result
        assert "Doc 2" in result
        assert "Doc 3" in result
