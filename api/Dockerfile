# Use the official Python image as a base image
FROM python:3.9-slim-buster

# Set the working directory
WORKDIR /code

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the entire application code to the working directory
COPY . .

EXPOSE 8000

# Set the command to run your application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
#still starts uvicorn on port 80 even after changing specified port
