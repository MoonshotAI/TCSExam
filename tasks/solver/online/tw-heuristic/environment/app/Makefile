# Build the solver at /app/solver.
# The judge copies /app to a scratch directory, runs `make`, and expects an
# executable file named `solver` in the top directory. `solver` is invoked
# once as:  solver INSTANCES_DIR OUTPUT_DIR POOL_SECONDS
#
# Baseline: the driver script (equal time slices) + FlowCutter core
# (PACE 2017 heuristic-track submission by Ben Strasser, BSD license, see
# src/LICENSE-flowcutter). Replace anything you like as long as `make`
# still produces ./solver honoring the same contract.

all: solver fc_bin

fc_bin: src/*.cpp src/*.h
	g++ -Wall -std=c++11 -O3 -DNDEBUG src/*.cpp -o fc_bin

solver: driver.sh
	cp driver.sh solver
	chmod +x solver

.PHONY: all clean
clean:
	rm -f solver fc_bin
