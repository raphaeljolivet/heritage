FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 8500

HEALTHCHECK CMD curl --fail http://localhost:8500/simulateur/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8500", "--server.address=0.0.0.0"]