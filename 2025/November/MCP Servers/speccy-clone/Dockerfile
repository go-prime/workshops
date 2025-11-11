# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server script
COPY getspecs.py /app/

# Expose the port
EXPOSE 8000

# Run FastMCP server with SSE transport
CMD ["fastmcp", "run", "getspecs.py", "--transport", "sse", "--port", "8000", "--host", "0.0.0.0"]