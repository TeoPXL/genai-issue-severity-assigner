import json
from model_client import chat
from prompt_templates import SYSTEM_PROMPT, FEW_SHOT




def agent_decide(text: str, seed_example=None):
messages = [{"role":"system","content":SYSTEM_PROMPT}] + FEW_SHOT + [{"role":"user","content": text}]
resp = chat(messages)
# Expect JSON; if the model returns extra text attempt to extract JSON
try:
parsed = json.loads(resp)
except Exception:
# fallback: try to find first {...}
import re
m = re.search(r"\{.*\}", resp, flags=re.S)
if m:
parsed = json.loads(m.group(0))
else:
raise
return parsed




def multi_agent_vote(text: str, n_agents=3):
votes = []
parsed_results = []
for i in range(n_agents):
parsed = agent_decide(text)
parsed_results.append(parsed)
votes.append(parsed.get("severity"))
# majority vote
winner = max(set(votes), key=votes.count)
# compute avg confidence
confidences = [p.get("confidence", 0.0) for p in parsed_results if p.get("severity")]
avg_conf = sum(confidences)/len(confidences) if confidences else 0.0
return {"severity": winner, "confidence": avg_conf, "votes": parsed_results}