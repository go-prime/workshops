FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy server script AND config files
COPY sendmail.py /app/
COPY config.json /app/
COPY mailing_list.json /app/

EXPOSE 8008

CMD ["fastmcp", "run", "sendmail.py", "--transport", "sse", "--port", "8008", "--host", "0.0.0.0"]