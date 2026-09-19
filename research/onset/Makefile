# One-command reproduction of every number in research/results/onset.json
# and research/results/onset_trajectory.json:   make all
N ?= 200000
RES = ../results

all: ant
	mkdir -p out out100k out500k
	./ant $(N) out
	python3 verify_py.py out 15000
	python3 analyze.py out $(RES) > out/analysis_stdout.txt
	./ant 100000 out100k && ./ant 500000 out500k
	grep -E '^(s|s_state|escape_step_margin20|periods_verified|mismatches_after_s)=' out100k/onset.txt out500k/onset.txt
	python3 render_check.py out $(RES)

ant: ant.c
	gcc -O2 -Wall -o ant ant.c -lm

clean:
	rm -rf ant out out100k out500k
