FROM python:3.12-slim-bookworm@sha256:356b0d18f9385f4bdcc673af60e1e64c9d1504952e4ec36ee32044c722a6bc4e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade --no-install-recommends --yes \
    && apt-get install --no-install-recommends --yes git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 basalt \
    && useradd --uid 10001 --gid basalt --create-home --shell /usr/sbin/nologin basalt
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "basalt-core @ git+https://github.com/kingsokafor777-droid/basalt-core@1b70c2c" \
    && pip install --no-cache-dir . \
    && chown -R basalt:basalt /app

USER 10001:10001
ENTRYPOINT ["basalt-rag"]
CMD ["--help"]
