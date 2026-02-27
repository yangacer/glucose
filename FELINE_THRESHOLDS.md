# Feline-Specific Threshold Calibration

## Overview

This application is calibrated for feline glucose monitoring. All threshold bands are adjusted to account for differences between human and feline glucose metabolism.

---

## Feline vs Human Glucose Ranges

| Metric | Cats | Humans |
|--------|------|--------|
| Normal Range | 70-150 mg/dL | 70-100 mg/dL (fasting) |
| Diabetic Target | 100-250 mg/dL | 80-130 mg/dL |
| Hypoglycemia | <60 mg/dL | <70 mg/dL |
| Hyperglycemia | >250 mg/dL | >180 mg/dL |

---

## Applied Thresholds

### CV (Coefficient of Variation)
Measures glucose variability as percentage.

| Band | Cat Range | Human Range | Rationale |
|------|-----------|-------------|-----------|
| Green | 0-25% | 0-20% | Cats naturally have higher variability |
| Yellow | 25-35% | 20-30% | Moderate variability acceptable |
| Red | >35% | >30% | High variability requiring attention |

---

### LBGI (Low Blood Glucose Index)
Measures hypoglycemia risk.

| Band | Cat Range | Human Range | Rationale |
|------|-----------|-------------|-----------|
| Green | 0-3.5 | 0-2.5 | Adjusted for feline hypoglycemia tolerance |
| Yellow | 3.5-7 | 2.5-5 | Moderate risk zone wider for cats |
| Red | >7 | >5 | High risk threshold elevated |

---

### HBGI (High Blood Glucose Index)
Measures hyperglycemia risk.

| Band | Cat Range | Human Range | Rationale |
|------|-----------|-------------|-----------|
| Green | 0-6 | 0-4.5 | Cats tolerate higher glucose better |
| Yellow | 6-12 | 4.5-9 | Reflects wider diabetic target range |
| Red | >12 | >9 | Sustained hyperglycemia threshold |

---

### ADRR (Average Daily Risk Range)
Combines LBGI + HBGI for overall risk assessment.

| Band | Cat Range | Human Range | Rationale |
|------|-----------|-------------|-----------|
| Green | 0-25 | 0-20 | Accounts for natural feline variation |
| Yellow | 25-50 | 20-40 | Wider acceptable daily range |
| Red | >50 | >40 | Combined risk threshold |

---

## Important Notes

### Stress Hyperglycemia
- Cats can exhibit glucose levels of 200-400+ mg/dL when stressed
- This is a normal physiological response in cats
- Readings should be taken in calm, familiar environments
- Multiple readings over time provide better assessment than single values

### Risk Metric Limitations
- LBGI/HBGI/ADRR formulas were originally developed for humans
- The transformation function `f(G) = 1.509 × (ln(G)^1.084 - 5.381)` centers on human glucose ~112.5 mg/dL
- Threshold bands are adjusted empirically based on veterinary guidelines
- These should be validated with your veterinarian for your specific cat

### Clinical Consultation
Always consult with a veterinarian regarding:
- Target glucose ranges for your individual cat
- Insulin dosing adjustments
- Interpretation of risk metrics
- Changes in diet or medication

---

## References

- Cornell University College of Veterinary Medicine - Feline Diabetes
- AAHA Diabetes Management Guidelines for Dogs and Cats
- Journal of Veterinary Internal Medicine - Glucose Monitoring in Diabetic Cats
- Clinical thresholds adapted from veterinary endocrinology literature

---

## Future Enhancements

Potential improvements for species-specific support:
- Configuration file for multiple species presets (cat, dog, human)
- UI toggle to switch between species profiles
- Database storage of user-selected species
- Species-specific normal ranges in summary timesheet color coding
- Validation of risk metric formulas against feline clinical data
