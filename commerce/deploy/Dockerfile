# Kundali commerce fulfilment service. Same pinned runtime as preview/Dockerfile. Compose overrides CMD (--host).
FROM python:3.13.17-bookworm AS builder
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels pyswisseph==2.10.3.2 tzdata==2026.5 reportlab==4.4.9 svglib==1.6.0 'fonttools[woff]==4.63.0' brotli==1.2.0 uharfbuzz==0.57.0

FROM python:3.13.17-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/kundali:/opt/kundali/src:/opt/kundali/prototype:/opt/kundali/commerce \
    SABPUJA_EPHE_PATH=/opt/kundali/ephe
WORKDIR /opt/kundali
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels pyswisseph==2.10.3.2 tzdata==2026.5 reportlab==4.4.9 svglib==1.6.0 'fonttools[woff]==4.63.0' brotli==1.2.0 uharfbuzz==0.57.0 \
 && groupadd --gid 10002 sbcommerce && useradd --uid 10002 --gid 10002 --no-create-home sbcommerce && rm -rf /wheels
COPY src/ /opt/kundali/src/
COPY prototype/kundali_prototype/ /opt/kundali/prototype/kundali_prototype/
COPY report/phase1 /opt/kundali/report/phase1
COPY commerce/sabpuja_commerce /opt/kundali/commerce/sabpuja_commerce
RUN chmod -R a+rX /opt/kundali
USER 10002:10002
EXPOSE 8770
CMD ["python", "-m", "sabpuja_commerce", "--config", "/run/sabpuja/commerce.json", "--smtp-config", "/run/sabpuja/smtp.json", "--port", "8770"]
