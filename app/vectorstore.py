import faiss
import numpy as np
import pickle
import os


class VectorStore:
    def __init__(self, dim=1536, store_path=os.getenv("VECTORSTORE_PATH","/data/vectorstore.pkl")):
        self.dim = dim
        self.store_path = store_path
        self._load()


    def _load(self):
        if os.path.exists(self.store_path):
            with open(self.store_path, "rb") as f:
                self.index, self.meta = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(self.dim)
            self.meta = []


    def add(self, embedding: np.ndarray, severity: str, ticket_text: str):
        if embedding.ndim == 1:
            vec = embedding.reshape(1, -1)
        else:
            vec = embedding
        self.index.add(vec.astype('float32'))
        for _ in range(vec.shape[0]):
            self.meta.append({"severity": severity, "text": ticket_text})
        self._save()


    def search(self, embedding: np.ndarray, k=5):
        if self.index.ntotal == 0:
            return []
        D, I = self.index.search(embedding.reshape(1, -1).astype('float32'), k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < len(self.meta):
                results.append((self.meta[idx], float(dist)))
        return results


    def _save(self):
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        with open(self.store_path, "wb") as f:
            pickle.dump((self.index, self.meta), f)