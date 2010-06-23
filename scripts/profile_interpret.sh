#!/usr/bin/env python
import pstats
p = pstats.Stats('gtg.prof')
p.strip_dirs().sort_stats("cumulative").print_stats(20)
