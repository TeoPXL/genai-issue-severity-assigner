from embeddings import embed_text
from vectorstore import VectorStore




def retrieve_context(query: str, store: VectorStore, k=3):
    q_emb = embed_text(query)
    results = store.search(q_emb, k)
    formatted = []
    for meta, dist in results:
        formatted.append(f"Severity:{meta['severity']} | Dist:{dist} | {meta['text']}")
    return "\n---\n".join(formatted), q_emb