#! /bin/env python3

# Expect input format is csv:
# 時間戳記,日期,胰島素時間,劑量,餵食時間,飲食,動作,餐前血糖值,餐前血糖測量時間,區段,時間區段,血糖值,測量時間,保健

# Convert the above csv to timestamp, glucose (mg/dL) format for time-weighted-mean.py
# timestamp maps to 時間戳記
# glucose maps to 血糖值 or 餐前血糖值, depending on which one is available

import sys

header = sys.stdin.readline().strip()
fields = header.split(",")
assert(fields[0].strip() == "時間戳記")
assert(fields[7].strip() == "餐前血糖值")
assert(fields[11].strip() == "血糖值")

if sys.argv[1] == 'glucose':
  for line in sys.stdin:
    fields = line.strip().split(",")
    timestamp = fields[0].strip()
    glucose = fields[11].strip() if fields[11].strip() else fields[7].strip()
    if glucose:
      print(f"{timestamp},{glucose}")
elif sys.argv[1] == 'insulin':
  for line in sys.stdin:
    fields = line.strip().split(",")
    timestamp = fields[0].strip()
    insulin_dose = fields[3].strip()
    if insulin_dose:
      print(f"{timestamp},{insulin_dose}")
