# Prompt Guard backend — matches the runtime dependency set used in production
# (ai_ml/requirements-runtime.txt, NOT the full ai_ml/requirements.txt — see
# that file's comment and DEPLOYMENT.md for why: installing the training-only
# transformers/torch dependencies into this image would add ~780MB of memory
# the running app never uses, since spaCy's backend auto-imports torch just
# because it's present).
#
# Build from the repo root (not backend/), since backend/main.py imports the
# ai_ml package as a sibling:
#   docker build -f backend/Dockerfile -t prompt-guard-backend .
#   docker run -p 8000:8000 -e CORS_EXTRA_ORIGINS=https://your-frontend.example prompt-guard-backend

FROM python:3.11-slim

WORKDIR /app

# System deps for spaCy/presidio's compiled extensions (preshed, thinc).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
COPY ai_ml/requirements-runtime.txt ai_ml/requirements-runtime.txt
RUN pip install --no-cache-dir \
    -r backend/requirements.txt \
    -r ai_ml/requirements-runtime.txt \
    && python -m spacy download en_core_web_sm

COPY backend/ backend/
COPY ai_ml/*.py ai_ml/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
