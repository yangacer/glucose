# Glucose & Insulin Prediction Feature

## Overview

Provide prediction of the next glucose level and recommended insulin dose based on historical data: past glucose levels, insulin doses, intake calories, and available metrics already defined in server.py.

**Goal:** Help users anticipate glucose trends and plan insulin dosing for the next time window.

---

## Requirements

### Data Source
- **Historical range:** 30 days (configurable parameter)
- **Prediction window:** Last 24 hours of glucose data
- **End point:** Last available glucose reading
- **Features:** Glucose levels, insulin doses, calorie intake, CV, LBGI/HBGI/ADRR

**Rationale for dual time windows:**
- **30-day lookback:** Used for calculating insulin-to-glucose ratios, CV (variability), confidence assessment, and baseline statistics
- **24-hour prediction:** Used for glucose prediction via time-weighted mean - emphasizes recent trends most relevant for immediate next window
- **Design philosophy:** Long history for context, recent data for prediction

### Prediction Target
- **Time window:** Next 12-hour period (Day: 05:00-16:59 or Night: 17:00-04:59)
- **Outputs:**
  - Predicted glucose level (mg/dL) with uncertainty range
  - Recommended insulin dose (units)
  - Confidence level (Low/Medium/High)

### UI Requirements
- **Location:** New section below "Summary Timesheet" in dashboard
- **Visual distinction:** Different color scheme, dashed borders, prominent "Prediction" label
- **Safety warnings:** Clear disclaimers about informational nature

---

## Algorithm Selection

### Chosen Approach: Statistical Baseline (Phase 1)

**Method:** Weighted moving average with insulin-to-glucose ratio

**Rationale:**
- ✅ **Simple & Interpretable:** Easy to understand and debug
- ✅ **No Training Required:** Works immediately with limited data
- ✅ **Fast Computation:** Sub-second execution time
- ✅ **Transparent Logic:** Users can see how predictions are made
- ✅ **Safe Baseline:** Conservative approach for medical application
- ✅ **Foundation for ML:** Can serve as fallback and comparison baseline

**Algorithm Steps:**

1. **Glucose Prediction:**
   ```
   - Fetch 30 days of historical glucose data
   - Extract last 24 hours for prediction (recent trend focus)
   - Convert to chronological order (ASC) for time-weighted mean
   - Calculate time-weighted mean using trapezoidal integration
   - Fallback to last 2 readings if insufficient 24h data
   - Fallback to simple average if all timestamps identical
   ```

2. **Insulin Recommendation:**
   ```
   - Fetch 30 days of insulin data
   - Pair insulin doses with glucose within 2-hour window
   - Calculate average insulin-to-glucose ratio
   - Apply ratio to predicted glucose
   - Adjust for recent calorie intake (up to 10% increase if >100 kcal)
   - Apply safety bounds (min=0, max=1.5× historical_max)
   ```

3. **Confidence Calculation:**
   ```
   - High: CV < 25%, >30 data points, stable recent trend
   - Medium: CV 25-35%, 14-30 data points, moderate variability
   - Low: CV > 35%, <14 data points, high variability or insufficient data
   ```

---

## Feature Engineering

### Primary Features
- **Recent glucose values:** Last 3-5 readings
- **Glucose trend:** Rate of change (rising, stable, falling)
- **Time window:** Day (AM) vs Night (PM)
- **Recent insulin:** Last 2-3 doses
- **Recent calories:** Last meal intake
- **Historical ratios:** Insulin-to-glucose, insulin-to-calorie

### Statistical Metrics (from server.py)
- **CV (Coefficient of Variation):** Measure of glucose variability
- **LBGI/HBGI:** Risk metrics for hypo/hyperglycemia
- **Time-weighted mean:** Average glucose accounting for time gaps

### Temporal Context
- Time since last insulin dose
- Time since last meal
- Historical patterns for current time window

---

## Implementation Details

### API Endpoint
```
GET /api/dashboard/prediction?lookback_days=30
```

**Response:**
```json
{
  "next_window": "Day (05:00-16:59)",
  "prediction": {
    "glucose": 145,
    "glucose_range": [120, 170],
    "insulin_recommended": 1.2,
    "confidence": "Medium"
  },
  "basis": {
    "data_points": 24,
    "lookback_days": 14,
    "recent_cv": 28.5,
    "avg_glucose": 140,
    "avg_insulin": 1.1
  },
  "warnings": [
    "High glucose variability detected",
    "Consult veterinarian if trend continues"
  ]
}
```

### Python Function Structure
```python
def predict_next_window(lookback_days=30):
    """
    Predict next glucose level and insulin dose using statistical baseline.
    
    Returns:
        dict: {
            'predicted_glucose': float,
            'glucose_range': tuple,
            'recommended_insulin': float,
            'confidence': str,
            'warnings': list
        }
    """
    # 1. Fetch historical data
    # 2. Calculate weighted glucose prediction
    # 3. Calculate insulin-to-glucose ratio
    # 4. Generate recommendation with safety bounds
    # 5. Assess confidence based on data quality
    # 6. Generate warnings if needed
```

### Safety Mechanisms

1. **Bounds Checking:**
   - Minimum insulin: 0 units
   - Maximum insulin: 1.5× historical maximum (configurable)
   - Glucose prediction capped at reasonable ranges (40-500 mg/dL)

2. **Data Quality Gates:**
   - Require minimum 7 days of data (half of default lookback)
   - Require at least 10 glucose readings
   - Flag predictions with high uncertainty

3. **Warning Triggers:**
   - Insufficient data (< 10 readings)
   - High variability (CV > 35%)
   - Unusual patterns (>2 std dev from mean)
   - Predicted hypoglycemia risk (< 60 mg/dL)
   - Predicted hyperglycemia risk (> 400 mg/dL)

4. **User Disclaimers:**
   - "For informational purposes only"
   - "Not a substitute for veterinary advice"
   - "Always verify with actual glucose readings"
   - "Consult veterinarian for dosing decisions"

---

## UI Design

### Prediction Section Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 🔮 Next Window Prediction                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Time Window: Day (05:00 - 16:59)                          │
│                                                             │
│  📊 Predicted Glucose: 145 mg/dL                           │
│      Expected range: 120 - 170 mg/dL                       │
│                                                             │
│  💉 Recommended Insulin: 1.2 units                         │
│                                                             │
│  Confidence: ●●●○○ Medium                                  │
│  Based on 30 days of historical data (24 readings)         │
│                                                             │
│  ⚠️ Warnings:                                               │
│  • Glucose variability is higher than usual                │
│  • Monitor closely and adjust as needed                    │
│                                                             │
│  ℹ️ Disclaimer: This prediction is for informational       │
│     purposes only. Always verify with actual glucose        │
│     readings and consult your veterinarian for dosing      │
│     decisions.                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Visual Design Tokens

**Colors:**
- Background: Light purple/blue (#e8eaf6)
- Border: Dashed 2px purple (#7e57c2)
- Text: Dark gray (#424242)
- Warning: Orange (#ff9800)

**Typography:**
- Section title: Bold, 1.2em
- Values: Bold, 1.1em
- Details: Regular, 0.9em
- Disclaimer: Italic, 0.85em

**Icons:**
- 🔮 Crystal ball for prediction
- 📊 Chart for glucose
- 💉 Syringe for insulin
- ⚠️ Warning for alerts
- ℹ️ Info for disclaimers

---

## Future Enhancements (Phase 2+)

### Machine Learning Integration

**When to Implement:**
- After collecting 3-6 months of dense data
- When statistical baseline shows limitations
- If user requests higher accuracy

**Potential Models:**
1. **Random Forest Regressor**
   - Handles non-linear relationships
   - Feature importance analysis
   - Requires moderate data (3-6 months)

2. **XGBoost/LightGBM**
   - Gradient boosting for accuracy
   - Fast training and prediction
   - Good with tabular data

3. **LSTM (Advanced)**
   - Captures temporal dependencies
   - Best for complex patterns
   - Requires 1+ year of data

**Hybrid Approach:**
- Use statistical baseline as fallback
- ML model for refinement/correction
- Ensemble predictions
- Continuous model evaluation

### Additional Features

1. **Personalization:**
   - Learn individual cat's patterns over time
   - Adjust predictions based on historical accuracy
   - Seasonal/weather factors (if relevant)

2. **Multi-step Predictions:**
   - Predict next 2-3 time windows
   - Show trajectory over next 24-48 hours
   - Confidence decreases with time horizon

3. **What-If Analysis:**
   - "If I give X units of insulin, expected glucose is Y"
   - Scenario planning for different meal sizes
   - Interactive dose calculator

4. **Continuous Learning:**
   - Update model as new data arrives
   - Track prediction accuracy over time
   - A/B testing different algorithms

5. **External Factors:**
   - Activity level tracking
   - Stress indicators
   - Medication changes
   - Environmental factors

---

## Validation & Monitoring

### Performance Metrics

**Glucose Prediction:**
- MAE (Mean Absolute Error): Target < 20 mg/dL
- RMSE (Root Mean Squared Error): Target < 30 mg/dL
- Within ±20% accuracy: Target > 80% of predictions

**Insulin Recommendation:**
- Safe dosing: 100% within veterinary guidelines
- Hypoglycemia prevention: Zero dangerous recommendations
- User satisfaction: Track actual doses used vs recommended

### Monitoring Dashboard

Track over time:
- Prediction vs actual glucose (scatter plot)
- Insulin recommendation vs actual dose used
- Confidence calibration (are "High" confidence predictions more accurate?)
- Warning trigger rates
- User feedback/overrides

---

## Development Phases

### Phase 1: Statistical Baseline (Current)
- **Timeline:** 2-4 weeks
- **Deliverables:**
  - Weighted moving average implementation
  - Basic insulin-to-glucose ratio calculation
  - UI section with disclaimers
  - API endpoint
  - Safety bounds and warnings

### Phase 2: Enhanced Features (3-6 months)
- **Timeline:** After collecting sufficient data
- **Deliverables:**
  - Improved confidence scoring
  - Time-of-day pattern recognition
  - Calorie intake adjustment
  - Historical accuracy tracking

### Phase 3: ML Integration (6-12 months)
- **Timeline:** When data volume supports ML
- **Deliverables:**
  - Random Forest or XGBoost model
  - A/B testing framework
  - Hybrid prediction (statistical + ML)
  - Model retraining pipeline

---

## Testing Strategy

### Unit Tests
- Weighted average calculation
- Insulin-to-glucose ratio
- Bounds checking
- Confidence level assignment

### Integration Tests
- API endpoint response format
- Database queries for historical data
- Edge cases (insufficient data, missing values)
- Safety mechanism triggers

### Validation Tests
- Compare predictions to holdout data
- Ensure no dangerous recommendations
- Test with various data scenarios
- Verify UI displays correctly

### User Acceptance
- Veterinary review of algorithm
- Safety validation with test cases
- Usability testing of UI
- Disclaimer clarity

---

## References

- **Feline Diabetes Management:** Veterinary guidelines for insulin dosing
- **Time Series Forecasting:** Statistical methods for prediction
- **Medical Device Safety:** FDA guidelines for clinical decision support
- **Existing Metrics:** CV, LBGI, HBGI, ADRR calculations in server.py
