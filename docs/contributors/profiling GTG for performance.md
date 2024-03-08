There are various tools to profile (measure) performance and identify problems.

* cProfile
* gprof2dot
* sysprof
* flameprof

# Profiling with cProfile

Python's [cProfile](http://docs.python.org/library/profile.html) allows profiling the whole GTG app. Do this following:

    ./launch.sh -p 'python3 -m cProfile -o gtg.prof'

Let GTG launch. Quit, and do the following to parse the results:

    $ ipython
    In [1]: import pstats
    In [2]: p = pstats.Stats('gtg.prof')
    In [3]: p.strip_dirs().sort_stats("cumulative").print_stats(20)

This should display profiling results, sorted by cumulative time, and displaying the top 20 contributors. Many others sorting possibilities are available, look at the [python documentation](http://docs.python.org/library/profile.html) to learn more about it. Here's an example of output with the above sorting configuration:

```
    Thu Aug  6 09:35:55 2009    gtg.prof

         453156 function calls (445719 primitive calls) in 3.799 CPU seconds

   Ordered by: cumulative time
   List reduced from 1197 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    3.802    3.802 <string>:1(<module>)
        1    0.000    0.000    3.802    3.802 {execfile}
        1    0.000    0.000    3.801    3.801 gtg:28(<module>)
        1    0.000    0.000    3.405    3.405 gtg.py:93(main)
        1    0.000    0.000    2.599    2.599 browser.py:1405(main)
        1    0.943    0.943    2.427    2.427 {gtk._gtk.main}
      142    0.003    0.000    1.283    0.009 browser.py:1320(on_task_added)
      961    0.009    0.000    0.917    0.001 tagtree.py:65(on_get_value)
     2056    0.060    0.000    0.911    0.000 {method 'get_value' of 'gtk.TreeModel' objects}
      200    0.002    0.000    0.892    0.004 requester.py:156(get_active_tasks_list)
      200    0.434    0.002    0.890    0.004 requester.py:96(get_tasks_list)
      142    0.003    0.000    0.888    0.006 tagtree.py:36(update_tags_for_task)
      142    0.017    0.000    0.870    0.006 {method 'row_changed' of 'gtk.TreeModel' objects}
      175    0.004    0.000    0.808    0.005 browser.py:796(tag_visible_func)
      142    0.009    0.000    0.330    0.002 tasktree.py:197(add_task)
       79    0.010    0.000    0.324    0.004 cleanxml.py:93(savexml)
        1    0.002    0.002    0.286    0.286 gtg.py:46(<module>)
       79    0.001    0.000    0.274    0.003 minidom.py:47(toprettyxml)
        2    0.000    0.000    0.273    0.137 __init__.py:148(save_datastore)
        1    0.000    0.000    0.272    0.272 __init__.py:81(get_backends_list)
```

# Graphical profiling charts with gprof2dot

Install [gprof2dot](https://github.com/jrfonseca/gprof2dot), then execute:

    ./launch.sh -p 'python3 -m cProfile -o gtg.prof'
    python gprof2dot.py -f pstats gtg.prof | dot -Tpng -o output.png

...and watch the resulting pretty image!

![Generated image](https://wiki.gnome.org/Apps/GTG/development?action=AttachFile&do=get&target=profile.png)

# Sysprof

Sysprof is a really cool graphical user interface for system-wide (or application-specific) profiling.
If it can be useful for profiling GTG, someone should document how to use it here...

# flameprof (flamegraph)

You can use [flameprof](https://pypi.org/project/flameprof/) to generate
an [flamegraph](https://www.brendangregg.com/flamegraphs.html), which roughly
shows what GTG does over time.

```sh
./launch.sh -p 'python3 -m cProfile -o gtg.prof'
flameprof -o gtg.svg gtg.prof
```

![Generated image (not GTG)](https://raw.githubusercontent.com/brendangregg/FlameGraph/main/example-perf.svg)
