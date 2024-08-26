FROM python:3.11.3-slim-bullseye

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV PIPENV_VENV_IN_PROJECT 1

# Install pipenv and use it to install Python dependencies
RUN pip install langchain langchain-openai python-dotenv python-telegram-bot fastapi uvicorn pymongo

# Copy the rest of the application code to the working directory
COPY *.py ./
COPY .env.prod ./.env

# Expose the port FastAPI will run on
EXPOSE 8080

# Run the web service on container startup. Here we use the uvicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to 
# handle instance scaling.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
