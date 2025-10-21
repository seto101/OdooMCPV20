FROM python:3.11-slim

# Metadata
LABEL maintainer="MCP Odoo Server"
LABEL version="2.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_server_odoo/ ./mcp_server_odoo/
COPY README.md LICENSE ./

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Set environment variables defaults
ENV SERVER_MODE=http \
    HOST=0.0.0.0 \
    PORT=5000 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json

# Run the application
CMD ["python", "-m", "mcp_server_odoo"]
