# ── Postgres (Docker Compose) ─────────────────────────────────────────────────
db-start:
	@docker compose up -d

db-stop:
	@docker compose down
