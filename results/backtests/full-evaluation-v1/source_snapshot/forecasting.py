from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class ForecastBundle:
    cutoff: pd.Timestamp
    load: np.ndarray
    pv: np.ndarray
    price: np.ndarray
    margin: np.ndarray
    metadata: dict
    candidates: dict


def historical_snapshot(actuals, cutoff):
    cutoff = pd.Timestamp(cutoff)
    return actuals.loc[actuals.available_at <= cutoff].copy(deep=True)


class ForecastProvider:
    def __init__(self, training_days=60, selection_days=14, calibration_days=28):
        self.training_days = training_days
        self.selection_days = selection_days
        self.calibration_days = calibration_days
        self.records = []

    @staticmethod
    def _features(values, dates, index):
        t = np.arange(144) / 144
        previous = values[index-1]
        week = values[max(0, index-7)]
        mean = values[max(0, index-7):index].mean(axis=0)
        dow = pd.Timestamp(dates[index]).dayofweek
        return np.column_stack([previous, week, mean,
                                np.full(144, previous.mean()),
                                np.sin(2*np.pi*t), np.cos(2*np.pi*t),
                                np.sin(4*np.pi*t), np.cos(4*np.pi*t),
                                np.full(144, dow >= 5)])

    def predict(self, history, cutoff):
        cutoff = pd.Timestamp(cutoff)
        if len(history) and history.available_at.max() > cutoff:
            raise ValueError('History contains unavailable labels')
        history = history.loc[history.interval_end <= cutoff]
        day_counts = history.groupby('date').size()
        full_dates = day_counts.index[day_counts == 144]
        history = history.loc[history.date.isin(full_dates)].sort_values('interval_start')
        m = len(history) // 144
        if not m:
            raise ValueError('At least one completed day is required')
        columns = ['load_kwh', 'pv_kwh', 'price_variable']
        values = history[columns].to_numpy().reshape(m, 144, 3)
        dates = list(full_dates) + [cutoff.date().isoformat()]
        candidates = {'yesterday': values[-1].copy(), 'last_week': values[max(0, m-7)].copy()}
        ridge = np.empty((144, 3))
        for k in range(3):
            v = values[:, :, k]
            if m >= 9:
                indices = range(max(7, m-self.training_days), m)
                x = np.vstack([self._features(v, dates, j) for j in indices])
                y = np.concatenate([v[j] for j in indices])
                scaler = StandardScaler().fit(x)
                model = Ridge(alpha=10.0).fit(scaler.transform(x), y)
                ridge[:, k] = model.predict(scaler.transform(self._features(v, dates, m)))
            else:
                ridge[:, k] = v[max(0, m-7):].mean(axis=0)
        candidates['ridge'] = ridge
        for a in candidates.values():
            a[:, :2] = np.maximum(a[:, :2], 0)
            a[:, 2] = np.maximum(a[:, 2], max(1e-6, values[:, :, 2].min()))
        eligible = [r for r in self.records if r['available_at'] <= cutoff][-self.selection_days:]
        selected, scores = [], {}
        for k, col in enumerate(columns):
            scores[col] = {name: float(np.mean([r['candidate_mse'][name][k] for r in eligible]))
                           for name in candidates} if eligible else {name: None for name in candidates}
            selected.append(min(candidates, key=lambda n: scores[col][n]) if eligible else 'last_week')
        prediction = np.column_stack([candidates[name][:, k] for k, name in enumerate(selected)])
        margin, quantile, validation_costs = self._margin(cutoff)
        metadata = {'cutoff': cutoff.isoformat(), 'training_label_cutoff': history.available_at.max().isoformat(),
                    'training_days_available': m, 'training_window_days': self.training_days,
                    'selection_validation_days': len(eligible), 'selected': dict(zip(columns, selected)),
                    'candidate_mse': scores, 'margin_quantile': quantile,
                    'margin_validation_cost_proxy': validation_costs,
                    'ridge_alpha': 10.0, 'ridge_scaling': 'training-fold-only',
                    'attachment3_used': False}
        return ForecastBundle(cutoff, prediction[:, 0], prediction[:, 1], prediction[:, 2],
                              margin, metadata, candidates)

    def _margin(self, cutoff):
        rows = [r for r in self.records if r['available_at'] <= cutoff][-self.calibration_days:]
        if not rows:
            return np.zeros(144), 0.8, {}
        errors = np.vstack([r['net_residual'] for r in rows])
        prices = np.vstack([r['price'] for r in rows])
        levels = [0.5, 0.65, 0.8, 0.9, 0.95]
        groups = np.arange(144) // 24
        def fit(a, level):
            return np.array([max(0, np.quantile(a[:, groups == g], level)) for g in groups])
        costs = {}
        if len(rows) >= 14:
            train, valid = errors[:-7], errors[-7:]
            for level in levels:
                b = fit(train, level)
                costs[str(level)] = float(np.mean(prices[-7:] * (b+5*np.maximum(valid-b, 0))))
            best = min(levels, key=lambda a: costs[str(a)])
        else:
            best = 0.8
        return fit(errors, best), best, costs

    def observe_completed_day(self, bundle, completed_actuals, settlement_price):
        if len(completed_actuals) != 144:
            raise ValueError('Only a complete labelled day may enter validation records')
        truth = completed_actuals[['load_kwh', 'pv_kwh', 'price_variable']].to_numpy()
        candidate_mse = {name: np.mean((x-truth)**2, axis=0).tolist()
                         for name, x in bundle.candidates.items()}
        self.records.append({'available_at': completed_actuals.available_at.max(),
                             'candidate_mse': candidate_mse,
                             'net_residual': truth[:, 0]-truth[:, 1]-bundle.load+bundle.pv,
                             'price': np.asarray(settlement_price).copy()})


def issued_pv_integrals(released_forecasts, issue_time, lead_zero_kw):
    issue_time = pd.Timestamp(issue_time)
    if (released_forecasts.available_at > issue_time).any():
        raise ValueError('Unpublished forecasts supplied to the forecast interface')
    rows = released_forecasts.loc[released_forecasts.issue_time == issue_time].sort_values('lead_time')
    if list(rows.lead_time) != list(range(1, 25)):
        raise ValueError('One complete forecast issue with leads 1..24 is required')
    boundary_kw = np.interp(np.arange(145)/6, np.arange(25),
                            np.r_[max(0, lead_zero_kw), np.maximum(rows.value.to_numpy(), 0)])
    return (boundary_kw[:-1]+boundary_kw[1:])/12
