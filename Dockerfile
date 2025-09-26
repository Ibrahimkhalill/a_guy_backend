FROM python:3.10-slim-bullseye

WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the code
COPY . .

# ⚠️ Don't run migrate or collectstatic here
# These will run at container runtime, so environment variables are available

CMD sh -c "python manage.py migrate && \
           python manage.py collectstatic --noinput && \
           uvicorn a_guy_main.asgi:application --host 0.0.0.0 --port ${PORT:-8000} --lifespan off"