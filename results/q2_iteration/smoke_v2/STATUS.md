# Preflight failure

This first smoke attempt stopped before forecasting or solving any day because pandas.Timestamp rejected numpy.str_. No numerical result was generated. The date representation was corrected to Python strings; smoke_v2_fixed and subsequent runs completed. Retained as a failed preflight record, not an evaluated strategy or omitted evaluation day.
