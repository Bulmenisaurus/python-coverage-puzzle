# python-coverage-puzzle

Try to execute every gcov-counted line of CPython's `Objects/listobject.c` by running small Python scripts. Coverage comes from a sibling checkout at `../cpython`, a normal GIL build of 3.14 compiled with `make coverage`. Override that path with `CPYTHON`.

Each run writes counters into a fresh directory, so one script cannot inherit another's `.gcda` data.

## One script

```bash
./coverage.sh test.py            # writes output.json
./coverage.sh test.py run.json   # writes run.json
```

Stats go to stderr (`targets`, `hit`, `missed`, `coverage`). The script's own prints stay on stdout. A failing script still produces a report.

## Baselines

`baselines/*.py` are kept scripts. `./baselines.py` measures each one and writes the union to `output_baseline.json`, in the same three lists. A line is hit if any baseline hits it.

Look through `missed` in `output_baseline.json`. If a line looks reachable, add it to an existing baseline or drop a new file in `baselines/`, then run `./baselines.py` again.

## Browser

`python3 server.py` to run a server on http://127.0.0.1:8000.

Relies on baselines
