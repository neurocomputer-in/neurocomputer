"""
Smart Router code - invokes LLM and parses JSON output.
"""
import json
import re

async def run(state, **kwargs):
    """
    Invoke LLM with history/text and return structured routing decision.
    """
    llm = state["__llm"]
    # Get prompt from state (injected by factory)
    system_prompt = state.get("__prompt", "")
    
    # Extract inputs
    history = kwargs.get("history", "")
    text = kwargs.get("text", "")
    skills = kwargs.get("skills", "")

    final_system = system_prompt.replace("{{skills}}", str(skills)) \
                                .replace("{{history}}", str(history)) \
                                .replace("{{text}}", str(text))

    # Determine if we should really replace them or if they are in the user msg.
    # The prompt.txt has them. So we should replace them there.
    # If variables are missing, replace with empty string.
    
    # Generate JSON
    try:
        # We pass an empty user_msg because the prompt.txt already contains the "User message: {{text}}" part
        # properly formatted. Alternatively, we could keep the prompt static and pass dynamic data here.
        # Given prompt.txt has {{variables}}, we should format it.
        
        # NOTE: BaseBrain.generate_json appends user_msg to system_prompt? 
        # No, it sends system and user separately.
        # If prompt.txt is the system prompt, we should render it.
        
        raw_output = llm.generate_json("", system_prompt=final_system)
        
    except Exception as e:
        print(f"[SmartRouter] LLM error: {e}")
        return {"action": "reply", "reply": "I'm having trouble thinking right now."}
    
    # Clean the output
    text = raw_output.strip()
    
    # Remove markdown code block wrappers
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Parse JSON
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                return {"action": "reply", "reply": text}
        except:
            return {"action": "reply", "reply": text}
    
    # Normalize result
    action = result.get("action", "reply")
    if action == "reply":
        return {
            "action": "reply",
            "reply": result.get("reply", "I'm not sure how to respond."),
            "skill": None,
            "params": {}
        }
    elif action == "skill":
        return {
            "action": "skill",
            "reply": None,
            "skill": result.get("skill", ""),
            "params": result.get("params", {})
        }
    else:
        return {"action": "reply", "reply": result.get("reply", str(result))}
