# 과제2를 한 단어로 돌리기 위한 Makefile.
# 컨테이너 안에서 실행한다 (Codespaces 터미널, 또는 docker compose exec lab bash).
#
#   make test        유닛 테스트 (tests/test_*.py)
#   make serve       단축 URL 웹 서버 (포트 8000)
#   make experiment         Step 6 개별 체이닝 탐지 횟수 실험
#   make compare-experiment Step 8 체이닝·선형 탐사 비교
#   make clean       캐시 정리
#
# 외부 라이브러리를 쓰지 않는다. Python 표준 모듈만으로 돈다.

PORT ?= 8000
HASH_TABLE ?= chaining

.PHONY: all test serve experiment compare-experiment clean

all: test

test:
	@python3 -m unittest discover -s tests -v

serve:
	@python3 src/server.py --port $(PORT) --hash-table $(HASH_TABLE)

experiment:
	@python3 experiments/probe_experiment.py

compare-experiment:
	@python3 experiments/compare_hash_tables.py

clean:
	rm -rf src/__pycache__ tests/__pycache__ experiments/__pycache__
