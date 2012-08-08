#!/usr/bin/env python2
import GTG.gtg
import cProfile
import pstats
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-d", "--debug",
               action="store_true", dest="debug", help="enable debug output")
(options, args) = parser.parse_args()

cProfile.run("GTG.gtg.main(options, args)", filename="gtg.profile")

p = pstats.Stats('gtg.profile')
p.sort_stats('cumulative').print_stats(15)
p.sort_stats('time').print_stats(15)
p.sort_stats('calls').print_stats(15)
