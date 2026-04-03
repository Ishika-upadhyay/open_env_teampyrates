FROM python:3.10
WORKDIR /app
COPY . /app
RUN pip install openenv-core pydantic openai
CMD ["python", "-c", "import environment; print('EV Environment is ready!')"]