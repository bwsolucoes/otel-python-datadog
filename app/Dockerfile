# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache, which can reduce image size.
# --trusted-host pypi.python.org: Sometimes needed in certain network environments.
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the current directory contents into the container at /app
COPY main.py .

# Make port 80 available to the world outside this container (if your app were a web server)
# Not strictly necessary for this client app, but good practice if it were serving.
# EXPOSE 80 

# Define environment variables (can also be set in docker-compose.yml)
# ENV NAME World

# Run main.py when the container launches
# PYTHONUNBUFFERED=1 ensures that Python output is sent straight to terminal without being buffered first
CMD ["python", "-u", "main.py"]