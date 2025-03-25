FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY chatbot_app ./chatbot_app

CMD ["uvicorn", "chatbot_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
