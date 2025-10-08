# #
# FROM python:3.10

# #
# WORKDIR /code

# #
# COPY ./requirements.txt /code/requirements.txt

# #
# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# #
# COPY ./app /code/app

# #
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080" , "--root-path", "/api/"]




# Use a slimmer base to speed up cold starts
FROM python:3.10-slim

# 1) Workdir
WORKDIR /app

# 2) Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy code
COPY . .

# 4) Cloud Run listens on $PORT (defaults to 8080)
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

# Optional (not required by Cloud Run, but self-documenting)
EXPOSE 8080

# 5) Start the server on $PORT; enable proxy headers for Cloud Run
CMD ["sh","-c","exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
