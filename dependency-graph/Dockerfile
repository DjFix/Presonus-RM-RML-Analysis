FROM python:3.12-slim
COPY requirements.txt /opt/graph/requirements.txt
RUN pip install --no-cache-dir -r /opt/graph/requirements.txt
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python"]
