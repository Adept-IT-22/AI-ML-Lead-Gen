# Stage 1 — Build Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY ./frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY ./frontend/ ./
RUN npm run build

# Stage 2 - Python Dependencies Builder
FROM python:3.11-slim AS python-builder
WORKDIR /app
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3 - Final Runtime Image
FROM python:3.11-slim
WORKDIR /app

# Copy Python packages from builder
COPY --from=python-builder /root/.local /root/.local

# Copy backend code
COPY ./backend .

# Copy frontend build
COPY --from=frontend-build /frontend/dist/lead-gen/browser/ ./static/

# Update PATH
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app

EXPOSE 5050

CMD ["gunicorn", "--worker-class", "gevent", "--bind", "0.0.0.0:5050", "--timeout", "300", "main:app"]