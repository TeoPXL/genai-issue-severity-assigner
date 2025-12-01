#!/usr/bin/env bash
# simple entry script to ensure vectorstore directory exists
mkdir -p /data
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info