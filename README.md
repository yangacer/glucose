1. Export csv from Google Sheets
2. Extract relevant columns

```
cat data.csv | ./extract.py >> input.csv
```

3. Run analysis for weakly time-weighted mean

```
cat input.csv | ./time-weighted-mean.py > out.week.csv
```

4. Run analysis for daily time-weighted mean

```
cat input.csv | ./time-weighted-mean.py --mode daily > out.day.csv
```


