"""
Tests for AIGenerator in ai_generator.py
Focus: Testing that AIGenerator correctly calls tools and handles responses
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator


class TestAIGeneratorToolCalling:
    """Test AIGenerator's tool calling functionality"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_without_tools(self, mock_anthropic_class, mock_claude_response_no_tool):
        """Test response generation without tool use"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_no_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Act
        response = generator.generate_response(query="What is Python?")

        # Assert
        assert response is not None
        assert "general knowledge" in response
        mock_client.messages.create.assert_called_once()

        # Verify API call structure
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 800
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert "What is Python?" in call_kwargs["messages"][0]["content"]

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_with_tools_registered(self, mock_anthropic_class, mock_claude_response_no_tool):
        """Test that tools are passed to Claude API when provided"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_no_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        tool_definitions = [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object", "properties": {}}
        }]

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions
        )

        # Assert
        assert response is not None
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tool_definitions
        assert "tool_choice" in call_kwargs
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_claude_uses_tool(
        self,
        mock_anthropic_class,
        mock_claude_response_with_tool,
        mock_claude_final_response,
        mock_tool_manager
    ):
        """Test full tool execution flow when Claude decides to use a tool"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First call: Claude requests tool use
        # Second call: Claude processes tool results
        mock_client.messages.create.side_effect = [
            mock_claude_response_with_tool,
            mock_claude_final_response
        ]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        tool_definitions = [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object", "properties": {}}
        }]

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert response is not None
        assert "MCP (Model Context Protocol)" in response

        # Verify two API calls were made
        assert mock_client.messages.create.call_count == 2

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="What is MCP?",
            course_name="Introduction to MCP Servers"
        )

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_flow_messages(
        self,
        mock_anthropic_class,
        mock_claude_response_with_tool,
        mock_claude_final_response,
        mock_tool_manager
    ):
        """Test that tool results are properly sent back to Claude"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            mock_claude_response_with_tool,
            mock_claude_final_response
        ]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        tool_definitions = [{"name": "search_course_content"}]
        mock_tool_manager.execute_tool.return_value = "Tool result: MCP info here"

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Assert - check second API call structure
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]

        # Should have 3 messages: user query, assistant tool use, user tool results
        assert len(second_call_kwargs["messages"]) == 3

        # First message: user query
        assert second_call_kwargs["messages"][0]["role"] == "user"

        # Second message: assistant's tool use request
        assert second_call_kwargs["messages"][1]["role"] == "assistant"

        # Third message: tool results
        assert second_call_kwargs["messages"][2]["role"] == "user"
        tool_result_content = second_call_kwargs["messages"][2]["content"]
        assert isinstance(tool_result_content, list)
        assert tool_result_content[0]["type"] == "tool_result"
        assert "Tool result: MCP info here" in tool_result_content[0]["content"]

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_with_conversation_history(self, mock_anthropic_class, mock_claude_response_no_tool):
        """Test that conversation history is included in system prompt"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_no_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        conversation_history = "User: Previous question\nAssistant: Previous answer"

        # Act
        response = generator.generate_response(
            query="Follow-up question",
            conversation_history=conversation_history
        )

        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        system_content = call_kwargs["system"]
        assert "Previous question" in system_content
        assert "Previous answer" in system_content

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_without_conversation_history(self, mock_anthropic_class, mock_claude_response_no_tool):
        """Test that system prompt works without conversation history"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_no_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Act
        response = generator.generate_response(query="What is Python?")

        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        system_content = call_kwargs["system"]
        assert "You are an AI assistant" in system_content
        assert "Previous conversation" not in system_content

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_error_handling(
        self,
        mock_anthropic_class,
        mock_claude_response_with_tool,
        mock_claude_final_response,
        mock_tool_manager
    ):
        """Test handling when tool execution returns an error"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = [
            mock_claude_response_with_tool,
            mock_claude_final_response
        ]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Tool returns error message
        mock_tool_manager.execute_tool.return_value = "No course found matching 'Nonexistent Course'"

        tool_definitions = [{"name": "search_course_content"}]

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Assert
        # Error message should be sent to Claude as tool result
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        tool_result = second_call_kwargs["messages"][2]["content"][0]
        assert "No course found" in tool_result["content"]

    @patch('ai_generator.anthropic.Anthropic')
    def test_multiple_tool_calls_in_single_response(self, mock_anthropic_class, mock_tool_manager):
        """Test handling multiple tool use blocks in single response"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create response with multiple tool uses
        mock_multi_tool_response = Mock()
        mock_multi_tool_response.stop_reason = "tool_use"

        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.id = "tool_1"
        tool_use_1.input = {"query": "MCP"}

        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "get_course_outline"
        tool_use_2.id = "tool_2"
        tool_use_2.input = {"course_name": "MCP"}

        mock_multi_tool_response.content = [tool_use_1, tool_use_2]

        mock_final = Mock()
        mock_final.stop_reason = "end_turn"
        mock_final_content = Mock()
        mock_final_content.text = "Combined answer"
        mock_final.content = [mock_final_content]

        mock_client.messages.create.side_effect = [mock_multi_tool_response, mock_final]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Act
        response = generator.generate_response(
            query="Tell me about MCP",
            tools=[{"name": "search_course_content"}, {"name": "get_course_outline"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert response == "Combined answer"
        # Both tools should be executed
        assert mock_tool_manager.execute_tool.call_count == 2

    @patch('ai_generator.anthropic.Anthropic')
    def test_two_sequential_tool_rounds(self, mock_anthropic_class, mock_tool_manager):
        """Test successful execution of 2 sequential tool rounds"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Claude uses get_course_outline
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        round1_tool = Mock()
        round1_tool.type = "tool_use"
        round1_tool.name = "get_course_outline"
        round1_tool.id = "tool_1"
        round1_tool.input = {"course_name": "MCP"}
        round1_response.content = [round1_tool]

        # Round 2: Claude uses search_course_content
        round2_response = Mock()
        round2_response.stop_reason = "tool_use"
        round2_tool = Mock()
        round2_tool.type = "tool_use"
        round2_tool.name = "search_course_content"
        round2_tool.id = "tool_2"
        round2_tool.input = {"query": "lesson 1 content", "lesson_number": 1}
        round2_response.content = [round2_tool]

        # Final response with text
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_content = Mock()
        final_content.text = "The course has 3 lessons. Lesson 1 covers MCP basics."
        final_response.content = [final_content]

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "Tool result"

        tool_definitions = [{"name": "get_course_outline"}, {"name": "search_course_content"}]

        # Act
        response = generator.generate_response(
            query="What are the lessons in MCP and explain lesson 1?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert response == "The course has 3 lessons. Lesson 1 covers MCP basics."
        assert mock_client.messages.create.call_count == 3  # Initial + 2 rounds
        assert mock_tool_manager.execute_tool.call_count == 2

    @patch('ai_generator.anthropic.Anthropic')
    def test_stops_at_two_round_limit(self, mock_anthropic_class, mock_tool_manager):
        """Test that tool execution stops after 2 rounds even if Claude wants more"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # All 3 responses request tool use
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.id = "tool_123"
        tool_use.input = {"query": "test"}
        tool_response.content = [tool_use]

        # Third response also has tool_use but should not be executed
        mock_client.messages.create.side_effect = [tool_response, tool_response, tool_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Act
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert mock_client.messages.create.call_count == 3  # Initial + 2 rounds
        assert mock_tool_manager.execute_tool.call_count == 2  # Only 2 rounds executed
        # Response should be empty string since 3rd response has no text, only tool_use
        assert response == ""

    @patch('ai_generator.anthropic.Anthropic')
    def test_stops_on_first_non_tool_response(self, mock_anthropic_class, mock_tool_manager):
        """Test early termination when Claude provides text response without tool use"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        round1_tool = Mock()
        round1_tool.type = "tool_use"
        round1_tool.name = "search_course_content"
        round1_tool.id = "tool_1"
        round1_tool.input = {"query": "test"}
        round1_response.content = [round1_tool]

        # Round 2: Text response (no tool use)
        round2_response = Mock()
        round2_response.stop_reason = "end_turn"
        round2_content = Mock()
        round2_content.text = "Here's the answer based on the search results."
        round2_response.content = [round2_content]

        mock_client.messages.create.side_effect = [round1_response, round2_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "Search results"

        # Act
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert response == "Here's the answer based on the search results."
        assert mock_client.messages.create.call_count == 2  # Only 2 API calls (not 3)
        assert mock_tool_manager.execute_tool.call_count == 1  # Only 1 tool execution

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_error_in_second_round(self, mock_anthropic_class, mock_tool_manager):
        """Test error handling when tool execution fails in round 2"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Successful tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        round1_tool = Mock()
        round1_tool.type = "tool_use"
        round1_tool.name = "search_course_content"
        round1_tool.id = "tool_1"
        round1_tool.input = {"query": "test"}
        round1_response.content = [round1_tool]

        # Round 2: Tool use that will fail
        round2_response = Mock()
        round2_response.stop_reason = "tool_use"
        round2_tool = Mock()
        round2_tool.type = "tool_use"
        round2_tool.name = "invalid_tool"
        round2_tool.id = "tool_2"
        round2_tool.input = {"query": "test"}
        round2_response.content = [round2_tool]

        # Final response after error
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_content = Mock()
        final_content.text = "I encountered an error with the second search."
        final_response.content = [final_content]

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        # First call succeeds, second call raises exception
        mock_tool_manager.execute_tool.side_effect = [
            "Success result",
            ValueError("Tool not found")
        ]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Act
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert "I encountered an error" in response
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify error was sent to Claude as tool result
        third_call_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        tool_result_message = third_call_messages[-1]  # Last message should be tool results
        assert tool_result_message["role"] == "user"
        assert "Tool execution error" in tool_result_message["content"][0]["content"]

    @patch('ai_generator.anthropic.Anthropic')
    def test_single_round_backward_compatibility(self, mock_anthropic_class, mock_tool_manager):
        """Test that single tool use still works as before (backward compatibility)"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        round1_tool = Mock()
        round1_tool.type = "tool_use"
        round1_tool.name = "search_course_content"
        round1_tool.id = "tool_1"
        round1_tool.input = {"query": "What is MCP?"}
        round1_response.content = [round1_tool]

        # Final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_content = Mock()
        final_content.text = "MCP is a protocol for AI tools."
        final_response.content = [final_content]

        mock_client.messages.create.side_effect = [round1_response, final_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "MCP info from database"

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert response == "MCP is a protocol for AI tools."
        assert mock_client.messages.create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1

    @patch('ai_generator.anthropic.Anthropic')
    def test_message_context_preservation_across_rounds(self, mock_anthropic_class, mock_tool_manager):
        """Test that message context is correctly preserved across multiple rounds"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        round1_tool = Mock()
        round1_tool.type = "tool_use"
        round1_tool.name = "get_course_outline"
        round1_tool.id = "tool_1"
        round1_tool.input = {"course_name": "MCP"}
        round1_response.content = [round1_tool]

        # Round 2: Another tool use
        round2_response = Mock()
        round2_response.stop_reason = "tool_use"
        round2_tool = Mock()
        round2_tool.type = "tool_use"
        round2_tool.name = "search_course_content"
        round2_tool.id = "tool_2"
        round2_tool.input = {"query": "lesson 1"}
        round2_response.content = [round2_tool]

        # Final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_content = Mock()
        final_content.text = "Final answer"
        final_response.content = [final_content]

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Act
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert - Check message structure in final API call
        final_call_messages = mock_client.messages.create.call_args_list[2][1]["messages"]

        # Should have 5 messages: user query, asst tool 1, user result 1, asst tool 2, user result 2
        assert len(final_call_messages) == 5

        # Verify message roles
        assert final_call_messages[0]["role"] == "user"  # Original query
        assert final_call_messages[1]["role"] == "assistant"  # Tool use 1
        assert final_call_messages[2]["role"] == "user"  # Tool result 1
        assert final_call_messages[3]["role"] == "assistant"  # Tool use 2
        assert final_call_messages[4]["role"] == "user"  # Tool result 2


class TestAIGeneratorConfiguration:
    """Test AIGenerator initialization and configuration"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_initialization(self, mock_anthropic_class):
        """Test AIGenerator initializes with correct parameters"""
        # Act
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Assert
        mock_anthropic_class.assert_called_once_with(api_key="test-key")
        assert generator.model == "claude-sonnet-4-20250514"
        assert generator.base_params["model"] == "claude-sonnet-4-20250514"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    def test_system_prompt_exists(self):
        """Test that system prompt is defined"""
        assert AIGenerator.SYSTEM_PROMPT is not None
        assert len(AIGenerator.SYSTEM_PROMPT) > 0
        assert "course materials" in AIGenerator.SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_tools(self):
        """Test that system prompt describes available tools"""
        prompt = AIGenerator.SYSTEM_PROMPT
        assert "search_course_content" in prompt
        assert "get_course_outline" in prompt


class TestAIGeneratorEdgeCases:
    """Test edge cases and error conditions"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_empty_query(self, mock_anthropic_class, mock_claude_response_no_tool):
        """Test handling of empty query string"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_no_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Act
        response = generator.generate_response(query="")

        # Assert
        # Should still make API call (no validation in current implementation)
        mock_client.messages.create.assert_called_once()

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_use_without_tool_manager(
        self,
        mock_anthropic_class,
        mock_claude_response_with_tool
    ):
        """Test behavior when Claude requests tool use but no tool_manager provided"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response_with_tool

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        tool_definitions = [{"name": "search_course_content"}]

        # Act
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions,
            tool_manager=None  # No tool manager!
        )

        # Assert
        # When tool_manager is None, loop is skipped and _extract_text_from_response is called
        # Since response only has tool_use blocks (no text), empty string is returned
        assert response == ""
        # Verify only 1 API call was made (no tool execution loop)
        mock_client.messages.create.assert_called_once()
