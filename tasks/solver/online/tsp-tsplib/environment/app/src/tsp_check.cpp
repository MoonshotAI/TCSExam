// Tour validator for the tsp-tsplib task — plays the role td-validate plays
// for the treewidth tasks.
//
// usage: tsp_check INSTANCE.tsp TOUR_FILE
//
// Exit 0 and print "valid <length>" on stdout iff TOUR_FILE is a permutation
// of 1..n (whitespace-separated integers, optional comment lines starting
// with 'c'); the length is computed under the instance's own
// EDGE_WEIGHT_TYPE. Otherwise exit 1 and print "invalid <reason>".
#include "tsplib.h"

int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s INSTANCE.tsp TOUR_FILE\n", argv[0]);
        return 2;
    }
    tsplib::Instance inst = tsplib::load(argv[1]);
    std::vector<int> tour;
    if (!tsplib::load_tour(argv[2], inst.n, tour)) {
        printf("invalid tour file (not a permutation of 1..%d)\n", inst.n);
        return 1;
    }
    int64_t len = tsplib::tour_length(inst, tour);
    printf("valid %lld\n", (long long)len);
    return 0;
}
