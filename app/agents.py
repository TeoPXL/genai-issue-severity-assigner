import json
from model_client import chat
from prompt_templates import SYSTEM_PROMPT, FEW_SHOT, PERSONALITY_PROMPTS, RANKING_PROMPT
from vectorstore import VectorStore
from rag import retrieve_context




def agent_decide(text: str, context: str = "", system_prompt: str = SYSTEM_PROMPT, seed_example=None):
    messages = [{"role":"system","content":system_prompt}] + FEW_SHOT
    if context:
        messages.append({"role": "user", "content": f"Retrieved Context:\n{context}"})
    messages.append({"role":"user","content": f"Ticket:\n{text}"})
    resp = chat(messages)
    import sys
    print(f"DEBUG: Raw response from chat: '{resp}'", file=sys.stderr)
    # Expect JSON; if the model returns extra text attempt to extract JSON
    try:
        parsed = json.loads(resp)
    except Exception:
        # fallback: find first '{' and use raw_decode
        start_idx = resp.find('{')
        if start_idx != -1:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(resp[start_idx:])
            except Exception:
                raise ValueError(f"Could not parse JSON from response: {resp}")
        else:
            raise ValueError(f"No JSON object found in response: {resp}")
    return parsed


def agent_rank(text: str, perspectives: list, system_prompt: str):
    # Construct the prompt
    perspectives_text = ""
    for i, p in enumerate(perspectives):
        perspectives_text += f"Perspective {i}:\nSeverity: {p.get('severity')}\nRationale: {p.get('rationale')}\n\n"
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Ticket:\n{text}\n\nPerspectives:\n{perspectives_text}"}
    ]
    
    resp = chat(messages)
    import sys
    print(f"DEBUG: Raw response from rank: '{resp}'", file=sys.stderr)
    
    try:
        parsed = json.loads(resp)
    except Exception:
         # fallback: find first '[' and use raw_decode
        start_idx = resp.find('[')
        if start_idx != -1:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(resp[start_idx:])
            except Exception:
                 # If list parsing fails, try to find numbers
                import re
                nums = re.findall(r'\d+', resp)
                parsed = [int(n) for n in nums[:3]]
        else:
             # If no list found, try to find numbers
            import re
            nums = re.findall(r'\d+', resp)
            parsed = [int(n) for n in nums[:3]]
            
    return parsed




def multi_agent_vote(text: str, n_agents=3):
    # Initialize store (loads from disk)
    store = VectorStore()
    context, _ = retrieve_context(text, store)
    
    votes = []
    parsed_results = []
    
    # Use personalities
    personalities = list(PERSONALITY_PROMPTS.keys())
    # If n_agents is specified, we can just use the first n, or cycle.
    # But the user asked for specific personalities. Let's use all of them if n_agents is not strictly enforcing a count.
    # Or better, let's just use the defined personalities.
    
    active_personalities = personalities[:n_agents] if n_agents <= len(personalities) else personalities
    
    for persona in active_personalities:
        prompt = PERSONALITY_PROMPTS[persona]
        print(f"DEBUG: Agent {persona} voting...")
        parsed = agent_decide(text, context=context, system_prompt=prompt)
        parsed['agent_name'] = persona # Add name to result
        parsed_results.append(parsed)
        votes.append(parsed.get("severity"))
        
    # --- Ranked Voting Round ---
    print("DEBUG: Starting Ranked Voting Round...")
    scores = {i: 0 for i in range(len(parsed_results))}
    
    for persona in active_personalities:
        prompt = PERSONALITY_PROMPTS[persona] + "\n" + RANKING_PROMPT
        # We append the ranking instructions to the persona prompt so they keep their character
        # actually RANKING_PROMPT is a system prompt itself. Let's just use RANKING_PROMPT but maybe inject persona?
        # The plan said "Call agent_rank(text, perspectives, system_prompt)".
        # Let's use the RANKING_PROMPT as base, but maybe prefix with "You are [Persona]"?
        # Actually, the RANKING_PROMPT says "You are a senior incident commander". 
        # Let's stick to the plan: "Call agent_rank for each".
        # If we want them to keep personality, we should probably mix them.
        # But for simplicity and robustness, let's use the RANKING_PROMPT as is, or maybe slightly modified.
        # Let's use RANKING_PROMPT.
        
        try:
            rankings = agent_rank(text, parsed_results, RANKING_PROMPT)
            print(f"DEBUG: Agent {persona} ranked: {rankings}")
            
            # Scoring: 1st=3, 2nd=2, 3rd=1
            if isinstance(rankings, list) and len(rankings) >= 1:
                if 0 <= rankings[0] < len(parsed_results): scores[rankings[0]] += 3
            if isinstance(rankings, list) and len(rankings) >= 2:
                if 0 <= rankings[1] < len(parsed_results): scores[rankings[1]] += 2
            if isinstance(rankings, list) and len(rankings) >= 3:
                if 0 <= rankings[2] < len(parsed_results): scores[rankings[2]] += 1
                
        except Exception as e:
            print(f"Error in ranking for {persona}: {e}")

    # Find winner
    winner_idx = max(scores, key=scores.get)
    winner_result = parsed_results[winner_idx]
    winner_severity = winner_result['severity']
    
    # compute avg confidence of the winner? Or just use the winner's confidence?
    # Let's use the winner's confidence.
    
    return {"severity": winner_severity, "confidence": winner_result.get('confidence', 0.0), "votes": parsed_results, "scores": scores}