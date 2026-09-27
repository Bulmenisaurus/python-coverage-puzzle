import sys

for name in sys.stdlib_module_names:
    try:
        __import__(name)
    except Exception:
        continue
