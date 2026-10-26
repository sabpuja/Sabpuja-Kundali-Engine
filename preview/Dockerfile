# Private client preview. Uses existing engine, no numerical change.
FROM python:3.13.17-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/kundali/src:/opt/kundali/prototype SABPUJA_EPHE_PATH=/opt/kundali/ephe
WORKDIR /opt/kundali
RUN python -m pip install --no-cache-dir --disable-pip-version-check pyswisseph==2.10.3.2 tzdata==2026.5 && groupadd --gid 10001 sabpuja && useradd --uid 10001 --gid 10001 --no-create-home sabpuja
COPY src/ /opt/kundali/src/
COPY prototype/kundali_prototype/ /opt/kundali/prototype/kundali_prototype/
RUN python -c 'import json,pathlib; p=pathlib.Path("/opt/kundali/prototype/kundali_prototype/places.json"); d=json.loads(p.read_text()); items=d["places"]; assert len(items)==12 and len([x for x in items if x["country"]=="India"])==10; d["places"]=[x for x in items if x["country"]=="India"]; d["status"]="PRIVATE CLIENT PREVIEW: 10 INDIAN CITY REFERENCE POINTS"; d["selection"]="India-only curated preview city references; test-only foreign entries omitted"; p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\\n")'
USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "kundali_prototype", "--port", "8765"]
