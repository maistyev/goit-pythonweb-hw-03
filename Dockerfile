FROM python:3.12-slim

WORKDIR /app

COPY . .

# Install required packages
RUN pip install jinja2

# Expose the application port
EXPOSE 3000

# Run the application
CMD ["python", "main.py"]