#!/bin/bash
export WORKERS=${FUNCTIONS_WORKER_PROCESS_COUNT:-10}
conda run --no-capture-output -n env uvicorn pipeline_ai:app --workers $WORKERS --host 0.0.0.0 --port 8080 --loop asyncio --timeout-keep-alive 6000 --log-level debug