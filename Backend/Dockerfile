# Stage 1 — Build Frontend
FROM node:20 AS frontend-build

WORKDIR /frontend

# Copy package files
COPY ./frontend/package*.json ./
RUN npm install --legacy-peer-deps

# Copy frontend source
COPY ./frontend/ ./

# Build production bundle
RUN npm run build

# Stage 2 - Backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements (if you have requirements.txt)
COPY ./backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY ./backend .

# Copy frontend build into static/
COPY --from=frontend-build /frontend/dist/lead-gen/browser/ ./static/

# Expose the port your Flask app runs on
EXPOSE 5000

# Set environment variable for Flask
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app

# Run the Flask app with Gunicorn
CMD ["gunicorn", "--worker-class", "gevent",  "--bind", "0.0.0.0:5000", "--timeout", "300", "main:app"]