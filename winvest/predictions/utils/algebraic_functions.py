import math

from statsmodels.tsa.api import ExponentialSmoothing


def linear(a, b, x):
    return a * x + b


def quadratic(a, b, c, x):
    return a * x**2 + b * x + c


def logarithmic(a, b, x):
    return a * math.log(x) + b


def exponential(a, b, x):
    return a * math.exp(x) + b


def holt_win(data, forecast_len):
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


def calculate_error(function, coefficients, data):
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
