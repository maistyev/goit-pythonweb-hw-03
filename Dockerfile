FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /app/templates /app/static/css /app/static/img /app/storage

COPY main.py /app/
COPY templates/*.html /app/templates/
COPY static/css/*.css /app/static/css/
COPY static/img/*.png /app/static/img/

RUN pip install jinja2

EXPOSE 3000

CMD ["python", "main.py"]