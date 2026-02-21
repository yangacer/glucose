#! /bin/env python3

# Expect input format is csv:
# 時間戳記,日期,胰島素時間,劑量,餵食時間,飲食,動作,餐前血糖值,餐前血糖測量時間,區段,時間區段,血糖值,測量時間,保健

# Convert the above csv to timestamp, glucose (mg/dL) format for time-weighted-mean.py
# timestamp maps to 時間戳記
# glucose maps to 血糖值 or 餐前血糖值, depending on which one is available

import sys
import re

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
elif sys.argv[1] == 'intake':
  food_info = {
    'Va': {
      'id':1,
      'energy': 1.16588235294118,
    },
    '好味': {
      'id': 2,
      'energy': 1.14814814814815,
    }
  }
  last_intakes = []
  for line in sys.stdin:
    fields = line.strip().split(",")
    timestamp = fields[0].strip()
    intakes = fields[5].strip().split('+')
    # for each intake, it is consist of food name, amount, and unit(g). e.g.
    # `milk200g`. The food name is UTF-8 string, and the amount is a number.
    # The unit is always 'g'.
    regex = r'([^\d]+)(\d+)(g)'
    if intakes:
      if intakes[0] == '同上':
        for intake in last_intakes:
          food_name, amount = intake
          info = food_info[food_name]
          print(f"{info['id']},{timestamp},{float(amount)},{float(amount) * info['energy']}")
      elif intakes[0]:
        last_intakes = []
        for intake in intakes:
          match = re.match(regex, intake)
          if match:
            food_name = match.group(1)
            amount = match.group(2)
            last_intakes.append((food_name, amount))
            info = food_info[food_name]
            print(f"{info['id']},{timestamp},{float(amount)},{float(amount) * info['energy']}")

