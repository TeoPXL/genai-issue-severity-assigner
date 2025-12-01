import pandas as pd
import os

DATA_PATH = os.getenv("DATA_PATH", "/data/tickets.csv")
try:
    df = pd.read_csv(DATA_PATH)
    print("Unique priorities:", df['priority'].unique())
    print("Value counts:\n", df['priority'].value_counts())
except Exception as e:
    print(e)
