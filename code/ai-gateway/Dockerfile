FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender1 \
       libgl1 \
       libegl1 \
       libgles2 \
       libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CPU-only in slim image (no NVIDIA runtime): skip CUDA init noise / cuInit errors from TensorFlow.
ENV CUDA_VISIBLE_DEVICES=-1
ENV TF_CPP_MIN_LOG_LEVEL=2

CMD ["python", "main.py"]
