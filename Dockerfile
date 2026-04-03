FROM python:3.10
WORKDIR /app

# Copy our game files into the container
COPY . /app

# Install the required libraries
RUN pip install openenv-core pydantic openai

# Open the specific port Hugging Face requires
EXPOSE 7860

# Launch the official OpenEnv game server
CMD ["openenv", "serve", "--host", "0.0.0.0", "--port", "7860"]