FROM ubuntu:latest
RUN apt-get update -qy
RUN apt-get install -qy python3.11 python3-pip python3.11-dev
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]