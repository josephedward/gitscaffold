FROM python:3.10-slim

WORKDIR /app

# Copy package and install
# Copy files and install package
COPY . /app
RUN pip install --no-cache-dir .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Entrypoint script handles inputs and invokes gitscaffold
ENTRYPOINT ["/app/entrypoint.sh"]