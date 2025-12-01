import pandas as pd
from embeddings import embed_texts
from vectorstore import VectorStore
import os


DATA_PATH = os.getenv("DATA_PATH", "/data/tickets.csv")


PRIORITY_MAP = {
    'very_low': 'low',
    'low': 'low',
    'medium': 'medium',
    'high': 'high',
    'critical': 'high'
}




def ingest_sample(limit=5000):
    df = pd.read_csv(DATA_PATH)
    # Basic sanitization: drop NA body
    df = df.dropna(subset=['body'])
    df['priority'] = df['priority'].fillna('Other')


    store = VectorStore()
    to_add = []
    texts = []
    metas = []
    for _, row in df.head(limit).iterrows():
        priority = str(row.get('priority', 'Other')).lower()
        severity = PRIORITY_MAP.get(priority, 'medium')
        text = (str(row.get('subject','')) + '\n' + str(row.get('body',''))).strip()
        texts.append(text)
        metas.append((severity, text))


    # batch embed
    batches = [texts[i:i+128] for i in range(0, len(texts), 128)]
    for i, batch in enumerate(batches):
        embs = embed_texts(batch)
        for j, emb in enumerate(embs):
            sev, t = metas[i*128 + j]
            store.add(emb, sev, t)
        print(f"Ingested {len(texts)} tickets into vectorstore.")




if __name__ == '__main__':
    ingest_sample(2000)