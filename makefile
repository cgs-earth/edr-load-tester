browser:
	uv run locust -H https://api.wwdh.internetofwater.app/

headless:
	uv run locust -H https://api.wwdh.internetofwater.app/ --headless

deps:
	uv sync --all-groups

check:
	uv run pyright && uv run ruff check