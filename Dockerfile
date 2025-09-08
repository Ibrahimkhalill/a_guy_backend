FROM python:3.10-slim-bullseye

WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy rest of the code
COPY . .

RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

CMD ["uvicorn", "a_guy_main.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "off"]
