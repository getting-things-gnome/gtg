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
    Generates a list of tuples (day, weekday), such that day is a string in
    the format ' %m/%d', and weekday is a string in the format '%a'.
    The list has a specific size @numdays, so that it represents the days
    starting from @start.

    @param start: a datetime object, first date to be included in the list
    @param numdays: integer, size of the list
    @return days: list of tuples, each containing a date in the format '%m/%d'
     and also an abbreviated weekday for the given date
    """
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    days = [(x.strftime("%m/%d"), x.strftime("%a")) for x in date_list]
    return days
