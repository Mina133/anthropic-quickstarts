.PHONY: dev up down logs

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker-compose up --build

down:
	docker-compose down -v

logs:
	docker-compose logs -f --tail=200


