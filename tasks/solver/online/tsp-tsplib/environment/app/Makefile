# Build the solver at /app/solver.
# The judge copies /app to a scratch directory, runs `make`, and expects an
# executable file named `solver` in the top directory. `solver` is invoked
# once per instance as:  solver INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
#
# Baseline: the driver script + the tsp_bin C++ solver (nearest neighbour,
# 2-opt, double-bridge ILS; TSPLIB parser in src/tsplib.h). Replace anything
# you like as long as `make` still produces ./solver honoring the same
# contract. The judge-side validator tsp_check is prebuilt in the image from
# the pristine sources — editing src/ does not change how tours are scored.

all: solver tsp_bin

tsp_bin: src/solver.cpp src/tsplib.h
	g++ -Wall -std=c++14 -O3 -DNDEBUG src/solver.cpp -o tsp_bin

solver: driver.sh
	cp driver.sh solver
	chmod +x solver

.PHONY: all clean
clean:
	rm -f solver tsp_bin
