import pstats
#p = pstats.Stats("wc-1K_v4_freeopt.prof")
#p = pstats.Stats("wc-1K_v5_funcset.prof")
p = pstats.Stats("wc-1K_v6_linetype.prof")
p.sort_stats("tottime")
#p.sort_stats("cumtime")
p.print_stats()
