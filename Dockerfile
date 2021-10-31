FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

VOLUME ./bot ./bot
VOLUME ./cfg.py ./cfg.py
VOLUME ./main.py ./main.py
