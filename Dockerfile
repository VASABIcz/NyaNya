FROM ludotech/python3.9-poetry
WORKDIR /app

RUN pip install --upgrade pip


COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .