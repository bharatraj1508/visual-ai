# Use a slim Python image for a smaller footprint
FROM python:3.14

# Set environment variables to optimize Python performance
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any are needed in the future)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code + Alembic config. alembic.ini lives at the api root
# (migrations themselves are under app/migrations); it MUST be present or
# `alembic upgrade head` in the migrate service can't find its config.
COPY alembic.ini .
COPY app/ ./app/
COPY scripts/ ./scripts/

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the FastAPI app using uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
