"""
API endpoint tests for the FastAPI application.
Tests all REST endpoints for proper request/response handling.
"""

import pytest
from unittest.mock import Mock, patch
from models import Source


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for /api/query endpoint"""

    def test_query_without_session_id(self, test_client, mock_rag_system):
        """Test query endpoint creates new session when session_id not provided"""
        # Arrange
        request_data = {
            "query": "What is MCP?"
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify session was created
        assert data["session_id"] == "session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify query was processed
        mock_rag_system.query.assert_called_once_with("What is MCP?", "session_1")

        # Verify answer content
        assert "MCP" in data["answer"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "Introduction to MCP Servers - Lesson 1"


    def test_query_with_existing_session_id(self, test_client, mock_rag_system):
        """Test query endpoint uses provided session_id"""
        # Arrange
        request_data = {
            "query": "Tell me more about MCP",
            "session_id": "session_42"
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify existing session was used
        assert data["session_id"] == "session_42"
        mock_rag_system.session_manager.create_session.assert_not_called()

        # Verify query was processed with correct session
        mock_rag_system.query.assert_called_once_with("Tell me more about MCP", "session_42")


    def test_query_with_sources(self, test_client, mock_rag_system):
        """Test query endpoint returns sources correctly"""
        # Arrange
        mock_sources = [
            Source(title="Course A - Lesson 1", url="https://example.com/a/1"),
            Source(title="Course B - Lesson 2", url="https://example.com/b/2")
        ]
        mock_rag_system.query.return_value = (
            "Answer with multiple sources",
            mock_sources
        )

        request_data = {"query": "Test query"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert len(data["sources"]) == 2
        assert data["sources"][0]["title"] == "Course A - Lesson 1"
        assert data["sources"][0]["url"] == "https://example.com/a/1"
        assert data["sources"][1]["title"] == "Course B - Lesson 2"
        assert data["sources"][1]["url"] == "https://example.com/b/2"


    def test_query_with_empty_sources(self, test_client, mock_rag_system):
        """Test query endpoint handles empty sources list"""
        # Arrange
        mock_rag_system.query.return_value = (
            "General knowledge answer without sources",
            []
        )

        request_data = {"query": "What is the capital of France?"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "General knowledge answer without sources"
        assert data["sources"] == []


    def test_query_missing_required_field(self, test_client):
        """Test query endpoint returns 422 for missing query field"""
        # Arrange
        request_data = {
            "session_id": "session_1"
            # Missing required 'query' field
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 422


    def test_query_empty_query_string(self, test_client, mock_rag_system):
        """Test query endpoint handles empty query string"""
        # Arrange
        request_data = {"query": ""}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        # Empty queries are still processed by RAG system
        mock_rag_system.query.assert_called_once()


    def test_query_exception_handling(self, test_client, mock_rag_system):
        """Test query endpoint handles RAG system exceptions"""
        # Arrange
        mock_rag_system.query.side_effect = Exception("Database connection failed")
        request_data = {"query": "Test query"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for /api/courses endpoint"""

    def test_get_courses_success(self, test_client, mock_rag_system):
        """Test courses endpoint returns statistics correctly"""
        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data content
        assert data["total_courses"] == 1
        assert len(data["course_titles"]) == 1
        assert data["course_titles"][0] == "Introduction to MCP Servers"

        # Verify method was called
        mock_rag_system.get_course_analytics.assert_called_once()


    def test_get_courses_multiple_courses(self, test_client, mock_rag_system):
        """Test courses endpoint with multiple courses"""
        # Arrange
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "Introduction to MCP Servers",
                "Advanced FastAPI",
                "Python Testing Best Practices"
            ]
        }

        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Introduction to MCP Servers" in data["course_titles"]
        assert "Advanced FastAPI" in data["course_titles"]
        assert "Python Testing Best Practices" in data["course_titles"]


    def test_get_courses_no_courses(self, test_client, mock_rag_system):
        """Test courses endpoint when no courses are loaded"""
        # Arrange
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []


    def test_get_courses_exception_handling(self, test_client, mock_rag_system):
        """Test courses endpoint handles exceptions"""
        # Arrange
        mock_rag_system.get_course_analytics.side_effect = Exception("ChromaDB not initialized")

        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 500
        assert "ChromaDB not initialized" in response.json()["detail"]


@pytest.mark.api
class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns expected message"""
        # Act
        response = test_client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert data["message"] == "RAG System API"


@pytest.mark.api
class TestRequestValidation:
    """Tests for request validation and error handling"""

    def test_query_invalid_json(self, test_client):
        """Test query endpoint rejects invalid JSON"""
        # Act
        response = test_client.post(
            "/api/query",
            data="invalid json {{{",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422


    def test_query_wrong_field_types(self, test_client):
        """Test query endpoint validates field types"""
        # Arrange
        request_data = {
            "query": 12345,  # Should be string
            "session_id": ["list", "not", "string"]  # Should be string
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 422


    def test_query_extra_fields_ignored(self, test_client, mock_rag_system):
        """Test query endpoint ignores extra fields"""
        # Arrange
        request_data = {
            "query": "Test query",
            "extra_field": "should be ignored",
            "another_field": 42
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        # Extra fields don't cause errors


@pytest.mark.api
class TestResponseFormats:
    """Tests for response format validation"""

    def test_query_response_format(self, test_client, mock_rag_system):
        """Test query response matches expected schema"""
        # Arrange
        request_data = {"query": "Test"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source structure
        if data["sources"]:
            source = data["sources"][0]
            assert "title" in source
            assert "url" in source
            assert isinstance(source["title"], str)
            assert isinstance(source["url"], str)


    def test_courses_response_format(self, test_client):
        """Test courses response matches expected schema"""
        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify course_titles contains strings
        for title in data["course_titles"]:
            assert isinstance(title, str)
