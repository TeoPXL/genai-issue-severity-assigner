SYSTEM_PROMPT = """
You are an incident triage assistant.
Given the ticket text and the retrieved context, assign one of: low, medium, high severity.
Return JSON only, no extra text. Schema:
{"severity": "low|medium|high", "confidence": 0.0-1.0, "rationale": "...", "evidence": ["...IDs or snippets..."]}
"""


FEW_SHOT = [
{
"role": "user",
"content": "Ticket: Checkout 500 errors, 65% error rate for checkout endpoint. Logs show DB write timeouts.
Expected: {\"severity\": \"high\", \"confidence\":0.95, \"rationale\":\"...\" }"
},
{
"role": "user",
"content": "Ticket: Minor CSS issue on account page visible only on Safari.
Expected: {\"severity\": \"low\", \"confidence\":0.8, \"rationale\":\"...\" }"
}
]