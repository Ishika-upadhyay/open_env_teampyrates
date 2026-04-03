FROM python:3.10
WORKDIR /app

# Copy our game files into the container
COPY . /app

# Install uv and the required libraries
RUN pip install uv openenv-core pydantic openai

# Open the specific port Hugging Face requires
EXPOSE 7860

# Launch the server using the recommended uv command
CMD ["uv", "run", "--project", ".", "server", "--host", "0.0.0.0", "--port", "7860"]