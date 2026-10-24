FROM node:22-bookworm-slim AS dashboard-build

WORKDIR /build/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# Reuse the agent image already deployed on the ECS host. It contains the
# dashboard's Python dependencies, so this avoids downloading a second Python
# base image and reinstalling the same packages during deployment.
FROM stochips-stock_agent:latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY services/agent/ /app/services/agent/
COPY dashboard/ /app/dashboard/
COPY --from=dashboard-build /build/dashboard/dist/ /app/dashboard/dist/

EXPOSE 8787
CMD ["python", "/app/dashboard/server.py", "--host", "0.0.0.0", "--port", "8787"]
