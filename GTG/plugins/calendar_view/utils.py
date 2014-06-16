import datetime
import random

random.seed(7)  # to generate same colors/dates every time


def random_color(mix=(0, 0.5, 0.5)):
    """
    Generates a random color based on the color @mix given as parameter.
    If the @mix color is the same every time, all the colors generated
    will be as from the same color pallete.

    param @mix: triple of floats, a color in the format (red, green, blue)
    """
    red = (random.random() + mix[0])/2
    green = (random.random() + mix[1])/2
    blue = (random.random() + mix[2])/2
    return (red, green, blue)


def date_generator(start, numdays):
    """
    Generates a list of dates (datetime objects) with a specific size @numdays,
    so that it represents the days starting from @start.

    @param start: a datetime object, first date to be included in the list
    @param numdays: integer, size of the list
    @return days: list of datetime objects, each containing a date
    """
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    return date_list
