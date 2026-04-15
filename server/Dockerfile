# Use an official lightweight Python runtime
FROM python:3.11-slim

# Set the working directory to /code
WORKDIR /code

# Copy the requirements file into the container at /code
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Hugging Face Spaces require running as a non-root user
# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory and update PATH
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's app directory
WORKDIR $HOME/app

# Copy the server directory contents into the container setting the owner to the user
COPY --chown=user . $HOME/app

# Command to run the FastAPI application on Hugging Face Spaces default port (7860)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
