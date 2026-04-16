    FROM python:3.11-slim

    # System deps (minimal, add more if you need parquet/arrow extras later)
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

    WORKDIR /workspace

    # Python deps
    COPY requirements.txt /workspace/requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    # Jupyter settings
    EXPOSE 8888

    CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

