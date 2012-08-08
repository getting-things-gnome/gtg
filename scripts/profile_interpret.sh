#!/usr/bin/env python2
import pstats
p = pstats.Stats('gtg.prof')
p.strip_dirs().sort_stats("cumulative").print_stats(20)
