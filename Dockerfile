FROM python:3.10
WORKDIR /app
COPY . /app
RUN pip install uv openenv-core pydantic openai
RUN pip install -e .
EXPOSE 7860
CMD ["uv", "run", "server", "--host", "0.0.0.0", "--port", "7860"]