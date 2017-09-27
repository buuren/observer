import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../observer')))

from observer import Observer
#print(sys.path)

start = time.time()
_sleep = 1
_count = 3
o = Observer(sleep=_sleep, count=_count)
o.generate_calculated_values()
print("Finished calculations in [%s] seconds" % (time.time() - start - (_sleep * (_count - 1))))

exit(0)