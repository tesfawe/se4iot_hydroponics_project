FROM python:3.9-slim

WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the simulation script into the container
COPY sensor_simulator.py .

# Command to run the script when the container starts
CMD ["python", "sensor_simulator.py"]