import math


def linear(a, b, x):
    return a * x + b


def quadratic(a, b, c, x):
    return a * x ** 2 + b * x + c


def logarithmic(a, b, x):
    return a * math.log(x) + b


def exponential(a, b, x):
    return a * math.exp(x) + b


def calculate_error(function, coefficients, data):
    error = 0.
    if function != logarithmic:
        for i in range(len(data)):
            error += (data[i] - function(*coefficients, i)) ** 2 / len(data)
    else:
        for i in range(len(data)):
            error += (data[i] - function(*coefficients, i + 1)) ** 2 / len(data)
    return error