#! /bin/env python3
# Extract glucose and insulin data from legacy CSV export.

# Expect input format is csv:
#
# 合併測量時間,選擇測量時間,時間戳記,測量時間,日期,血糖種類,Column 16,GAHD血糖,血糖 (mg/dL),Column 17,數值,胰島素劑量(格),施打時間,備註,餵食,體重(kg),分數

import sys

header = sys.stdin.readline().strip()
fields = header.split(",")

if sys.argv[1] == 'glucose':
  for line in sys.stdin:
    fields = line.strip().split(",")
    timestamp = fields[0].strip()
    glucose = fields[8].strip()
    if glucose:
      print(f"{timestamp},{glucose}")

elif sys.argv[1] == 'insulin':
  for line in sys.stdin:
    fields = line.strip().split(",")
    timestamp = fields[0].strip()
    insulin_dose = fields[11].strip()
    if insulin_dose:
      print(f"{timestamp},{insulin_dose}")
