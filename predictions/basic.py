import sys

sys.path.append("..")

from math import exp, log

from models.response_model import History, Method

from .utils.algebraic_functions import (calculate_error, exponential, linear,
                                        logarithmic, quadratic, holt_win)


def linear_approximation(history: History) -> Method:
    data = list(zip(*history.history))[1]

    alpha1_1 = 0
    alpha2 = 0
    sum_x = 0
    sum_y = 0
    for i in range(len(data)):
        alpha1_1 += i * data[i] * 1.0 / len(data)
        alpha2 += i * i * 1.0 / len(data)
        sum_x += i * 1.0 / len(data)
        sum_y += data[i] * 1.0 / len(data)
    a = (alpha1_1 - sum_x * sum_y) / (alpha2 - sum_x * sum_x)
    b = sum_y - a * sum_x

    method = Method(
        name = 'Линейная',
        type = 'lin',
        data = [a, b],
        error = calculate_error(linear, (a, b), data)
    )

    return method


def quadratic_approximation(history: History) -> Method:
    data = list(zip(*history.history))[1]

    alpha2_1 = 0.
    alpha1_1 = 0.
    alpha0_1 = 0.
    alpha4 = 0.
    alpha3 = 0.
    alpha2 = 0.
    alpha1 = 0.
    for i in range(len(data)):
        alpha2_1 += data[i] * i ** 2 / len(data)
        alpha1_1 += data[i] * i / len(data)
        alpha0_1 += data[i] / len(data)
        alpha4 += i ** 4 / len(data)
        alpha3 += i ** 3 / len(data)
        alpha2 += i ** 2 / len(data)
        alpha1 += i / len(data)
    k = (alpha1_1 - alpha0_1 * alpha1) * (alpha3 - alpha2 * alpha1) / (alpha2 - alpha1 ** 2)
    a = (alpha2_1 - alpha0_1 * alpha2 - k) / (
            alpha4 - alpha2 ** 2 - ((alpha3 - alpha2 * alpha1) ** 2 / (alpha2 - alpha1 ** 2)))
    b = (alpha1_1 - alpha0_1 * alpha1 - a * (alpha3 - alpha2 * alpha1)) / (alpha2 - alpha1 ** 2)
    c = alpha0_1 - a * alpha2 - b * alpha1

    method = Method(
        name = 'Квадратическая',
        type = 'quad',
        data = [a, b, c],
        error = calculate_error(quadratic, (a, b, c), data)
    )

    return method


def logarithmic_approximation(history: History) -> Method:
    data = list(zip(*history.history))[1]

    alpha1_1 = 0.
    alpha0_1 = 0.
    alpha2 = 0.
    alpha1 = 0.
    for i in range(len(data)):
        alpha1_1 += data[i] * log(i + 1) / len(data)
        alpha0_1 += data[i] / len(data)
        alpha2 += log(i + 1) ** 2 / len(data)
        alpha1 += log(i + 1) / len(data)
    a = (alpha1_1 - alpha0_1 * alpha1) / (alpha2 - alpha1 ** 2)
    b = alpha0_1 - a * alpha1

    method = Method(
        name = 'Логарифмическая',
        type = 'log',
        data = [a, b],
        error = calculate_error(logarithmic, (a, b), data)
    )

    return method


def exponential_approximation(history: History) -> Method:
    data = list(zip(*history.history))[1]

    alpha1_1 = 0.
    alpha0_1 = 0.
    alpha2 = 0.
    alpha1 = 0.
    for i in range(len(data)):
        alpha1_1 += data[i] * exp(i) / len(data)
        alpha0_1 += data[i] / len(data)
        alpha2 += exp(i) ** 2 / len(data)
        alpha1 += exp(i) / len(data)
    a = (alpha1_1 - alpha0_1 * alpha1) / (alpha2 - alpha1 ** 2)
    b = alpha0_1 - a * alpha1

    method = Method(
        name = 'Экспоненциальная',
        type = 'exp',
        data = [a, b],
        error = calculate_error(exponential, (a, b), data)
    )

    return method


def holt_win_fcast(history: History) -> Method:
    data = list(zip(*history.history))[1]

    fcast_len = 30
    train_index = int(0.75 * len(data))
    data_to_train = data[:train_index]
    data_to_test = data[train_index:]
    test_fcast = holt_win(data_to_train, len(data_to_test))
    fcast = holt_win(data, fcast_len)

    method = Method(
        name = 'Holt-win',
        type = 'holt-win',
        data = fcast,
        error = calculate_error(holt_win, test_fcast, data_to_test)
    )

    return method
