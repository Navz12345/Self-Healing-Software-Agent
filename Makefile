.PHONY: reproduce test lint loadtest demo clean download-data download-models

reproduce:
	docker compose down -v
	docker compose build
	docker compose up -d
	sleep 180
	make test

test:
	docker compose exec -T orchestrator sh -c "COVERAGE_FILE=/tmp/sha_coverage python -m pytest tests/ \
		--ignore=tests/test_json_eval.py \
		--cov=. --cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage_html \
		--cov-fail-under=70 \
		--junitxml=reports/unit.xml \
		-q"

lint:
	python -m ruff check . --no-cache
	python -m black --check .
	python -m mypy . --ignore-missing-imports
	mkdir -p reports
	pip-audit --format json -o reports/security.txt

loadtest:
	locust -f tests/load/locustfile.py \
		--headless -u 10 -r 2 --run-time 60s \
		--host http://localhost:8000 \
		--json > reports/benchmarks.json

demo:
	bash scripts/demo.sh

download-data:
	@echo "No external datasets required. RAG runbook is bundled at rag/runbook.md"
	@echo "ChromaDB is seeded automatically on first docker compose up"

download-models:
	@echo "No model download required. all-MiniLM-L6-v2 is cached by sentence-transformers"
	@echo "GPT-4o is accessed via OpenAI API - set OPENAI_API_KEY in .env"

clean:
	docker compose down -v
