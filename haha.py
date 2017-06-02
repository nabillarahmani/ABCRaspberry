import time
import datetime
ts = time.time()
ts = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H:%M:%S')

print(ts)