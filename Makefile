.PHONY: setup backend frontend mcp dev test check clear tunnel share build serve

NODE_BIN := $(CURDIR)/.tools/node/bin

setup:
	bash scripts/setup.sh

backend:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && PATH="$(NODE_BIN):$$PATH" npm run dev

mcp:
	cd mcp-server && PATH="$(NODE_BIN):$$PATH" npm start

dev:
	PATH="$(NODE_BIN):$$PATH" npx --yes concurrently -k -n api,web,mcp -c blue,magenta,green "make backend" "make frontend" "make mcp"

test:
	cd backend && ../.venv/bin/python -m pytest

clear:
	curl -s -X POST http://127.0.0.1:8000/api/data/clear && echo

tunnel:
	bash scripts/tunnel.sh mcp

share: build
	bash scripts/tunnel.sh share

check:
	bash scripts/check.sh

build:
	cd frontend && PATH="$(NODE_BIN):$$PATH" npm run build

serve: build
	cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
