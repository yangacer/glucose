#! /bin/env python3

# Expect input format is csv:
# timestamp, glucose (mg/dL)
# yyyy/MM/dd  hh:mm:ss, integer

import sys
import datetime
import argparse

def TimeWeightedMean(data):
  if len(data) < 2:
    return None
  total_area = 0.0
  total_time = 0.0
  for i in range(1, len(data)):
    t0, v0 = data[i-1]
    t1, v1 = data[i]
    delta_t = (t1 - t0).total_seconds()
    area = (v0 + v1) / 2.0 * delta_t
    total_area += area
    total_time += delta_t
  if total_time == 0:
    return None
  return total_area / total_time

parser = argparse.ArgumentParser(description='Calculate time-weighted mean glucose levels')
parser.add_argument('--mode', choices=['weekly', 'daily'], default='weekly',
                    help='Calculate weekly or daily means (default: weekly)')
args = parser.parse_args()

field1, field2 = sys.stdin.readline().split(",")
assert(field1.strip() == "timestamp" and field2.strip() == "glucose (mg/dL)")

all_data = []
for line in sys.stdin:
  timestamp, glucose = line.strip().split(",")
  glucose = int(glucose)
  time = datetime.datetime.strptime(timestamp, "%Y/%m/%d  %H:%M:%S")
  all_data.append((time, glucose))

# sort and unique data by timestamp
all_data.sort(key=lambda x: x[0])
all_data = list(dict(all_data).items())

def process_data(get_period_key, format_period):
  last_period = None
  period_data = []
  for time, glucose in all_data:
    current_period = get_period_key(time)
    period_data.append((time, glucose))
    if last_period is None:
      last_period = current_period
    if last_period < current_period:
      mean = TimeWeightedMean(period_data)
      print(f"{format_period(last_period)},{mean:.2f}")
      period_data = [(time, glucose)]
      last_period = current_period
  mean = TimeWeightedMean(period_data)
  print(f"{format_period(last_period)},{mean:.2f}")

if args.mode == 'weekly':
  print("year/week,time-weighted mean glucose (mg/dL)")
  process_data(
    lambda t: (t.isocalendar()[0], t.isocalendar()[1]),
    lambda p: f"{p[0]}/W{p[1]:02d}"
  )
else:  # daily mode
  print("date,time-weighted mean glucose (mg/dL)")
  process_data(
    lambda t: t.date(),
    lambda d: d.strftime('%Y/%m/%d')
  )
