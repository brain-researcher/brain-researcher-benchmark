FROM ubuntu:24.04
# Pinned to the versions that ran the Step-0 probe (step0/outputs/pip_freeze.txt; that host ran
# Python 3.14, and every pin below has a cp312 manylinux_2_28 wheel for this image's Python 3.12).
# The data is not in the image: ~20 GB of OpenNeuro ds001907 derivatives are fetched at runtime.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates python3 python3-venv python3-pip curl && \
    python3 -m pip install --break-system-packages --no-cache-dir \
      numpy==2.5.3 \
      scipy==1.18.1 \
      scikit-learn==1.9.1 \
      pandas==3.0.6 \
      nibabel==5.4.2 \
      nilearn==0.14.1 && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
