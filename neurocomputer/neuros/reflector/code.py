import json

async def run(state, *, action: str = "", result: str = "", goal: str = "", observations: str = ""):
    """
    Self-reflection neuro that evaluates action results.
    
    Returns:
        should_replan: bool - whether to trigger replanning
        reason: str - explanation
        suggestion: str - what to do if replanning
        ask_user: bool - whether to ask user for input
        user_question: str - question to ask if ask_user is True
    """
    llm = state["__llm"]
    system = state.get("__prompt", "")
    
    payload = json.dumps({
        "goal": goal,
        "action": action,
        "result": result[:1000] if result else "",  # Truncate long results
        "observations": observations
    }, ensure_ascii=False)
    
    raw = llm.generate_json(payload, system_prompt=system)
    
    try:
        obj = json.loads(raw)
        return {
            "should_replan": obj.get("should_replan", False),
            "reason": obj.get("reason", ""),
            "suggestion": obj.get("suggestion"),
            "ask_user": obj.get("ask_user", False),
            "user_question": obj.get("user_question")
        }
    except Exception:
        # Default to continue if parsing fails
        return {
            "should_replan": False,
            "reason": "Reflection parsing failed, continuing",
            "suggestion": None,
            "ask_user": False,
            "user_question": None
        }
