import numpy as np
from model_client import embed




def embed_text(text: str) -> np.ndarray:
    # calls remote embed endpoint with single string and returns a numpy array
    embs = embed([text])
    vec = np.array(embs[0], dtype="float32")
    return vec




def embed_texts(texts: list) -> np.ndarray:
    embs = embed(texts)
    return np.array(embs, dtype="float32")