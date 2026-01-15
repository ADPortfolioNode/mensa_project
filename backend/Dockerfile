# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
# Remove httptools if present in any dependency, and use h11 as HTTP implementation
RUN pip install --no-cache-dir -r requirements.txt && pip uninstall -y httptools

# Copy the rest of the backend code
COPY . .

# Command to run the application
# Use h11 instead of httptools to avoid memory allocation issues
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--http", "h11"]
