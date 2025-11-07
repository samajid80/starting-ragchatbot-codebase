import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
- **get_course_outline**: Get course structure, title, link, instructor, and complete lesson list
- **search_course_content**: Search for specific content within course materials

Tool Usage Guidelines:
- Use **get_course_outline** for questions about course structure, overview, lessons list, or what a course covers
- Use **search_course_content** for questions about specific course content or detailed educational materials
- **Up to two rounds of tool use per query** - You may use tools in an initial round, then optionally use tools again based on the results
- **Strategic tool sequencing**: For complex queries, use get_course_outline first to understand structure, then search_course_content for specific details
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

When to Use Each Tool:
- **Course outline questions** (use get_course_outline): "What lessons are in X?", "Show me the outline of Y", "What does course Z cover?"
- **Course content questions** (use search_course_content): "How do I implement X?", "What is Y in lesson 3?", "Explain Z concept"
- **General knowledge questions**: Answer using existing knowledge without using any tools

Multi-Round Tool Strategy:
- **Discovery then detail**: First get course outline to identify relevant lessons, then search specific content within those lessons
- **Filter refinement**: Use initial search results to inform more targeted follow-up searches with specific course or lesson filters
- **Comparison queries**: Search for content from different courses or lessons separately, then synthesize the comparison
- **Always provide final synthesis**: After using tools, synthesize all results into a coherent, direct answer

Response Protocol:
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the results" or "I used the tool"
- When presenting course outlines, include the course title, course link, instructor, and complete lesson list with numbers and titles

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_tool_rounds: int = 2) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to max_tool_rounds sequential tool calls.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages list and round tracking
        messages = [{"role": "user", "content": query}]
        round_count = 0

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        # Add tools if available (keep them throughout all rounds)
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get initial response from Claude
        response = self.client.messages.create(**api_params)

        # Iterative tool execution loop - continue while Claude requests tools
        while (response.stop_reason == "tool_use" and
               round_count < max_tool_rounds and
               tool_manager is not None):

            round_count += 1

            # Append assistant's tool use response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls from this response
            tool_results = self._execute_tool_round(response, tool_manager)

            # If tool execution failed critically, break loop
            if tool_results is None:
                break

            # Append tool results as user message
            messages.append({"role": "user", "content": tool_results})

            # Make next API call with updated messages (tools still available)
            api_params["messages"] = messages
            response = self.client.messages.create(**api_params)

        # Extract and return final text response
        return self._extract_text_from_response(response)

    def _execute_tool_round(self, response, tool_manager) -> Optional[List[Dict]]:
        """
        Execute all tool calls from a response and return results.

        Args:
            response: The API response containing tool use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dictionaries, or None if no tools to execute
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    # Execute the tool
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

                except Exception as e:
                    # Return error as tool result so Claude can handle it
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Tool execution error: {str(e)}",
                        "is_error": True
                    })

        return tool_results if tool_results else None

    def _extract_text_from_response(self, response) -> str:
        """
        Safely extract text content from API response.

        Args:
            response: The API response object

        Returns:
            Extracted text string, or empty string if no text found
        """
        for content_block in response.content:
            # Check if this is a text block (not tool_use)
            if hasattr(content_block, 'type') and content_block.type != "tool_use":
                if hasattr(content_block, 'text'):
                    return content_block.text
            # For blocks without type attribute, check for text attribute
            elif not hasattr(content_block, 'type') and hasattr(content_block, 'text'):
                # Verify it's actually a string, not a Mock
                if isinstance(content_block.text, str):
                    return content_block.text

        # Fallback: if no text block found, return empty string
        return ""

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text