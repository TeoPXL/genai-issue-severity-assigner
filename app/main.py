from fastapi import FastAPI
from pydantic import BaseModel
from vectorstore import VectorStore
from rag import retrieve_context
from agents import multi_agent_vote
from embeddings import embed_text

app = FastAPI(title="Severity Classifier API")
store = VectorStore()

class TicketIn(BaseModel):
    subject: str
    body: str

class TicketOut(BaseModel):
    severity: str
    confidence: float
    votes: list
    context_used: str


@app.post('/classify', response_model=TicketOut)
def classify(ticket: TicketIn):
    text = f"{ticket.subject}\n{ticket.body}"

    # Retrieve similar historical cases (RAG)
    context, q_emb = retrieve_context(text, store)

    # Multi-agent severity voting
    vote_res = multi_agent_vote(
        f"Context:\n{context}\n---\nTicket:\n{text}"
    )

    # Store embedding + final chosen severity
    store.add(q_emb, vote_res['severity'], text)

    return {
        'severity': vote_res['severity'],
        'confidence': float(vote_res['confidence']),
        'votes': vote_res['votes'],
        'context_used': context
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
