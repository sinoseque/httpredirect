.PHONY: test install

test:
	.venv/bin/python -m pytest -q

install:
	.venv/bin/pip install -r requirements.txt
