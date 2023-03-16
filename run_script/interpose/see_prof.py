import pstats
p = pstats.Stats("output.prof")
p.sort_stats("tottime")
p.print_stats()
