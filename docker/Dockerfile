FROM node:24-alpine AS web
WORKDIR /build/frontend
RUN npm install -g pnpm@11.19.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY backend/ backend/
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-deps .
COPY alembic.ini ./
COPY migrations/ migrations/
COPY --from=web /build/frontend/dist frontend/dist/
RUN useradd --create-home --uid 10001 lottolab && mkdir /data && chown -R lottolab:lottolab /app /data
USER lottolab
EXPOSE 8000
CMD ["uvicorn", "lottolab.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
