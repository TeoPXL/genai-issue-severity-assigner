import pandas as pd
import argparse
import os
import sys
import shutil

# Add the current directory to sys.path to allow imports if run from app dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import multi_agent_vote
from ingestion import PRIORITY_MAP
from vectorstore import VectorStore
from embeddings import embed_texts

# Default data path assuming running from root or app
DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets.csv")
VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", "/data/vectorstore.pkl")

def run_batch(n=10, data_path=None):
    if data_path is None:
        data_path = os.getenv("DATA_PATH", DEFAULT_DATA_PATH)
    
    print(f"Loading data from {data_path}...")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"Error: File not found at {data_path}")
        return

    # Basic sanitization
    df = df.dropna(subset=['body'])
    df['priority'] = df['priority'].fillna('Other')
    
    # --- Few-Shot Setup ---
    print("Setting up few-shot examples...")
    
    # Clear existing vector store
    if os.path.exists(VECTORSTORE_PATH):
        print(f"Clearing vector store at {VECTORSTORE_PATH}")
        os.remove(VECTORSTORE_PATH)
        
    # Select 1 example for each severity
    seed_indices = []
    severities_found = set()
    
    # We want low, medium, high. 'Other' maps to medium usually.
    target_severities = ['low', 'medium', 'high']
    
    for index, row in df.iterrows():
        priority = str(row.get('priority', 'Other')).lower()
        severity = PRIORITY_MAP.get(priority, 'medium')
        
        if severity in target_severities and severity not in severities_found:
            seed_indices.append(index)
            severities_found.add(severity)
        
        if len(severities_found) == len(target_severities):
            break
            
    if not seed_indices:
        print("Warning: Could not find examples for all severities.")

    # Ingest seeds
    seed_rows = df.loc[seed_indices]
    
    texts = []
    metas = []
    
    for _, row in seed_rows.iterrows():
        priority = str(row.get('priority', 'Other')).lower()
        severity = PRIORITY_MAP.get(priority, 'medium')
        text = (str(row.get('subject','')) + '\n' + str(row.get('body',''))).strip()
        texts.append(text)
        metas.append((severity, text))
        print(f"Seeding with example for {severity}")

    if texts:
        embs = embed_texts(texts)
        dim = embs.shape[1]
        print(f"Detected embedding dimension: {dim}")
        
        store = VectorStore(store_path=VECTORSTORE_PATH, dim=dim)
        
        for i, emb in enumerate(embs):
            sev, t = metas[i]
            store.add(emb, sev, t)
        print("Seeding complete.")
        
    # --- Evaluation ---

    total = 0
    correct = 0
    results = []

    print(f"Processing next {n} issues (excluding seeds)...")
    
    # Exclude seeds from evaluation
    eval_df = df.drop(seed_indices)
    
    # Limit to n items
    subset = eval_df.head(n)
    
    for index, row in subset.iterrows():
        subject = str(row.get('subject', ''))
        body = str(row.get('body', ''))
        text = f"{subject}\n{body}".strip()
        
        # Get actual severity
        actual_priority = str(row.get('priority', 'Other')).lower()
        actual_severity = PRIORITY_MAP.get(actual_priority, 'medium')
        
        print(f"\n--- Issue {index} ---")
        print(f"Subject: {subject[:50]}...")
        
        # Predict
        try:
            vote_res = multi_agent_vote(text)
            predicted_severity = vote_res['severity']
            confidence = vote_res['confidence']
            rationale = vote_res.get('votes', [{}])[0].get('rationale', 'No rationale provided')
            
            print(f"Predicted: {predicted_severity} (Conf: {confidence:.2f})")
            print(f"Actual: {actual_severity}")
            print(f"Rationale: {rationale[:100]}...")
            
            if predicted_severity == actual_severity:
                correct += 1
                print("Result: CORRECT")
            else:
                print("Result: INCORRECT")
                
            results.append({
                "index": index,
                "predicted": predicted_severity,
                "actual": actual_severity,
                "correct": predicted_severity == actual_severity
            })
            
            # Add to vector store for future context (optional, but good for "online" learning if desired, 
            # but user asked for "next n ones it may fare better" which implies using the static seeds or growing?
            # User said: "That way, when running on the next n onesm it may fare better."
            # and "make sure that this vector store is cleared and generated each time we run"
            # So static seeds are definitely required. Adding processed ones is a bonus but maybe not strictly requested.
            # I will stick to just using the seeds for now to be safe and consistent.)
            
        except Exception as e:
            print(f"Error processing issue {index}: {e}")
        
        total += 1

    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n\n=== Summary ===")
        print(f"Processed: {total}")
        print(f"Correct: {correct}")
        print(f"Accuracy: {accuracy:.2f}%")
    else:
        print("No issues processed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch evaluation for severity assigner.")
    parser.add_argument("--n", type=int, default=10, help="Number of issues to process")
    parser.add_argument("--data", type=str, help="Path to tickets.csv")
    
    args = parser.parse_args()
    
    run_batch(n=args.n, data_path=args.data)
