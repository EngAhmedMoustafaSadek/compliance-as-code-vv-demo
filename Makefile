.PHONY: test review trace verify clean

test:
	pytest --junitxml=reports/junit.xml || true

review:
	python tools/llm_review.py

trace:
	python tools/trace.py

verify: test review trace

clean:
	rm -rf reports .pytest_cache
