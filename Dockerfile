FROM python:3.11-slim

# ffmpeg o‘rnatish
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]