import math
from typing import Any, Callable, List, Tuple

from statsmodels.tsa.api import ExponentialSmoothing


def linear(a: float, b: float, x: float) -> float:
    return a * x + b


def quadratic(a: float, b: float, c: float, x: float) -> float:
    return a * x**2 + b * x + c


def logarithmic(a: float, b: float, x: float) -> float:
    return a * math.log(x) + b


def exponential(a: float, b: float, x: float) -> float:
    return a * math.exp(x) + b


def holt_win(data: List[float], forecast_len: int) -> Any:
    seasonal_period = min(60, len(data) // 3)
    exp_fit = ExponentialSmoothing(
        data,
        seasonal_periods=seasonal_period,
        trend='add',
        seasonal='add',
        damped_trend=True,
    ).fit()
    exp_forecast = exp_fit.forecast(forecast_len)
    return exp_forecast


def calculate_error(
    function: Callable[..., float],
    coefficients: Tuple[float],
    data: Any,
) -> float:
    error = 0.0
    if function == holt_win:
        for i in range(len(data)):
            error += (data[i] - coefficients[i]) ** 2 / len(data)
    elif function != logarithmic:
        for i in range(len(data)):
            error += (data[i] - function(*coefficients, i)) ** 2 / len(data)
    else:
        for i in range(len(data)):
            error += (data[i] - function(*coefficients, i + 1)) ** 2 / len(data)
    return error
