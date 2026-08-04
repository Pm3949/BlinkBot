import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger("websocket")

async def analyze_and_optimize_query(message: str, llm) -> dict:
    """
    Analyzes the user's message intent and sentiment, and generates an optimized search query.
    """
    system_prompt = (
        "You are an expert AI intent analyzer and query preprocessor.\n"
        "Your task is to analyze the user's message and output a JSON object containing:\n"
        "1. 'intent': The primary goal of the user's message. Use one of these specific values: \n"
        "   - 'greeting': Casual conversation starter or greeting (e.g., 'hi', 'hello', 'how are you').\n"
        "   - 'factual_rag': General factual queries, technical questions, information retrieval, doc search.\n"
        "   - 'support': Requesting customer support details, returns, refunds, store policy.\n"
        "   - 'other': Out of scope, off-topic, or miscellaneous questions.\n"
        "2. 'sentiment': User sentiment classification ('neutral', 'frustrated', 'positive').\n"
        "3. 'optimized_query': An expanded, detailed, and clear version of the query optimized for semantic search / vector databases. Make sure to fix any typos, add necessary context, and keep it specific to the search keywords.\n\n"
        "Output ONLY a valid JSON object. Do not include markdown codeblocks or extra text. Example:\n"
        "{\"intent\": \"factual_rag\", \"sentiment\": \"neutral\", \"optimized_query\": \"...\"}"
    )

    try:
        # Bind JSON response format if supported, or just request it
        try:
            llm_json = llm.bind(response_format={"type": "json_object"})
        except Exception:
            llm_json = llm

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Message: {message}")
        ]
        
        response = await llm_json.ainvoke(messages)
        content = response.content
        
        # Parse content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            content = "".join(parts)
        elif isinstance(content, dict):
            content = content.get("text", str(content))
        
        content = content.strip()
        
        # Strip codeblock wrappers if any
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            import ast
            try:
                parsed = ast.literal_eval(content)
            except Exception as ast_err:
                logger.error(f"ast.literal_eval parsing failed: {ast_err}")
                raise ValueError("Response is not valid JSON or dict literal")

        return {
            "intent": parsed.get("intent", "factual_rag"),
            "sentiment": parsed.get("sentiment", "neutral"),
            "optimized_query": parsed.get("optimized_query", message)
        }
    except Exception as e:
        logger.error(f"Error in analyze_and_optimize_query: {e}")
        # Fallback to defaults
        return {
            "intent": "factual_rag",
            "sentiment": "neutral",
            "optimized_query": message
        }
