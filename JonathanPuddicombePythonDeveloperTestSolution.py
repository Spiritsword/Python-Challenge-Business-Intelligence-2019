"""
Please write you name here: Jonathan Puddicombe
"""

import csv
import operator
import math
from pathlib import Path
from pprint import pprint

# NB MUCH EXCEPTION CHECKING CODE WOULD NORMALLY BE REQUIRED
# BUT THIS HAS BEEN OMITTED AS THE TEST SPEC SAID 'NO ALERTS'.

# Functions to manipulate time format


def hour_and_minute(time_string):
    # Extract hour and minute from a time string.
    hour, minute = map(int, time_string.split(':'))
    return (hour, minute)


def hour_to_time(hour):
    # Convert hour to hour-and-(zero)-minute string format.
    return (str(hour) + ":" + "00")


def min_to_hr_convert(minute):
    # Convert minute to proportion of hour.
    minute = float(minute)
    return (minute/60)


# Functions to help parse the string in the break_notes field of
# the work_shifts file


def parse_time(time_string):
    # This parses a time string (i.e. either start or end time)
    # within the break_note string.

    # Remove spaces from string.
    time_string = time_string.replace(' ', '')
    
    # Iterate through the characters of the hour part of string
    # to extract the hour.

    # Initialise.
    time_string_length = len(time_string)
    cursor = 0
    current_char = time_string[cursor]
    digits = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')
    hour = ''
    minute = ''
    # Iterate.
    while current_char in digits:
        hour = hour + current_char
        # Increment cursor.
        cursor += 1 
        if cursor == time_string_length:
            # At end of string?
            # Hour has been completely extracted.
            break
        current_char = time_string[cursor]
    # Convert hour string to integer.
    hour = int(hour)

    # Extract minute similarly (positioned after '.' or ':').
    if current_char == '.' or current_char == ':':
        # Increment cursor to start of minute string.
        cursor += 1 
        current_char = time_string[cursor]
        while current_char in digits:
            minute = minute + current_char
            cursor += 1
            if cursor == time_string_length:
                # At end of string?
                # Minute has been completely extracted.
                break
            # Update current_char to prepare for next iteration.
            current_char = time_string[cursor]
        # Convert minute string to integer.
        minute = int(minute)
    else:
        # If no minute string then assume minute is zero.
        minute = 0
    # Is there another character?
    if cursor < time_string_length:
        current_char = time_string[cursor]
        # And does "PM" follow?
        if current_char == 'P':
            # Adjust hour
            hour = hour + 12

    return (hour, minute)


def parse_break_note(break_note):
    # This is the top-level parse function
    # for the break_notes field.
    # It splits a break_note string into two time strings
    # (start and end times), which are then parsed.

    break_start_string, break_end_string = break_note.split('-')
    break_start_hour, break_start_minute = parse_time(
        break_start_string)
    break_end_hour, break_end_minute = parse_time(
        break_end_string)

    return (
        break_start_hour, break_start_minute,
        break_end_hour, break_end_minute)


# Functions to build the hourly cost dictionary
# from work_shifts table


def work_shift_times(row):
# Extract start and end times of shift and break from
# a row in work_shifts. Minutes are converted to part hour
# and added to the relevant integer hour to give a float.

    # Extract and process shift times.
    shift_start_hour, shift_start_minute = hour_and_minute(
        row['start_time'])
    w_s_t = {}
    w_s_t['shift_start'] = shift_start_hour + min_to_hr_convert(
        shift_start_minute)
    shift_end_hour, shift_end_minute = hour_and_minute(
        row['end_time'])
    w_s_t['shift_end'] = shift_end_hour + min_to_hr_convert(
        shift_end_minute)

    # Extract and process break times.
    break_start_hour, break_start_minute, \
    break_end_hour, break_end_minute  = parse_break_note(
        row['break_notes'])
    w_s_t['break_start'] = break_start_hour + min_to_hr_convert(
        break_start_minute)
    w_s_t['break_end'] = break_end_hour + min_to_hr_convert(
        break_end_minute)

    # Semantic analysis: reinterpret break times if necessary.
    # If break_start is before shift_start then reinterpret
    # break_start and break_end as 'pm'.
    if w_s_t['break_start'] < w_s_t['shift_start']:
        if w_s_t['break_start'] < 12:       
            w_s_t['break_start'] += 12
        if w_s_t['break_end'] < 12:        
            w_s_t['break_end'] += 12

    return w_s_t


def hourly_time_worked(row):
    # Build a dictionary with key = hour and
    # value = time worked for a single row of the work_shifts
    # table i.e value is the payable time for that hour of that
    # particular employee's shift.

    # Extract shift and break times for the row.
    w_s_t = work_shift_times(row)

    # Extract the (integer) hours from these (float) times.
    shift_start_hour = math.floor(w_s_t['shift_start'])
    break_start_hour = math.floor(w_s_t['break_start'])
    break_end_hour = math.floor(w_s_t['break_end'])
    shift_end_hour = math.floor(w_s_t['shift_end'])
    
    # Hours will be iterated through and, for each hour, the
    # payable time will be calculated and the value stored
    # in 'hourly_time_worked_dict'.

    # There are four stages to pass through, depending on
    # where the current (imaginary) time-pointer is in relation
    # to start and end of the shift and start and end of
    # the break.

    # Transitions from one stage to the next may occur part-way
    # through an hour and there maybe zero, one or more than one
    # transition(s) in any particular hour.

    # Initialise hour as the hour of start of shift.
    hour = shift_start_hour
    # Initialise stage to first hour of shift (but notionally
    # the shift has not yet quite begun).
    stage = 'first_hour'
    # Initialise dictionary to accumulate chargeable time.
    hourly_time_worked_dict = {}
    # Initialise shift as 'ongoing': the end of the shift has not yet
    # been reached. When shift_ongoing changes to False then iteration
    # finishes.
    shift_ongoing = True
    # Iterate through the hours.
    while shift_ongoing:
        # 'fresh_hour = True' means that the hour is 'fresh' i.e. no
        # if-statement has yet triggered (evaluated as true) during
        # the current hour.
        fresh_hour = True

        if stage == 'first_hour':
            # Base value needs to be set because hour is fresh.
            # If no stage change occurs then this is the payable time
            # (in hours) that will be attributed to the current
            # hour.
            hours_worked_this_hour = 0
            fresh_hour = False
            # Adjust payable time for shift starting part-way
            # through the hour. (This must always happen because
            # this first hour in the iteration was defined to be when
            # the shift starts.)
            hours_worked_this_hour += (hour + 1 - w_s_t['shift_start'])
            # Transition to the next stage.
            stage = 'pre_break_start'
 
        if stage == 'pre_break_start':
            if fresh_hour:
                # Set base value for payable time if hour is
                # still fresh. (Otherwise use tally so far
                # calculated in this hour as the base.)
                hours_worked_this_hour = 1
                fresh_hour = False
            # If break starts during this hour...
            if break_start_hour == hour:
                # ...adjust payable time appropriately.
                hours_worked_this_hour -= (hour + 1 - w_s_t['break_start'])
                stage = 'between_break_start_and_break_end'

        if stage == 'between_break_start_and_break_end':
            if fresh_hour:
                hours_worked_this_hour = 0
                fresh_hour = False
            # If break ends during this hour...
            if break_end_hour == hour:
                # ...adjust payable time appropriately.
                hours_worked_this_hour += (hour + 1 - w_s_t['break_end'])
                stage = 'post_break_end'

        if stage == 'post_break_end':
            if fresh_hour:
                hours_worked_this_hour = 1
                fresh_hour = False
            # If shift ends during this hour...
            if shift_end_hour == hour:
                # ...adjust payable time appropriately...
                hours_worked_this_hour -= (hour + 1 - w_s_t['shift_end'])
                # ...and the shift has ended so this is the last
                # iteration necessary.
                shift_ongoing = False

        # Update output dictionary to include this hour's time worked.
        hourly_time_worked_dict[hour] = hours_worked_this_hour
        # Increment hour in preparation for next iteration.
        hour += 1

    return hourly_time_worked_dict                                                  


# FUNCTIONS REQUIRED BY CHALLENGE  


def process_shifts(path_to_csv):
    """

    :param path_to_csv: The path to the work_shift.csv
    :type string:
    :return: A dictionary with time as key (string) with format %H:%M
        (e.g. "18:00") and cost as value (Number)
    For example, it should be something like :
    {
        "17:00": 50,
        "22:00: 40,
    }
    In other words, for the hour beginning at 17:00, labour cost was
    50 pounds
    :rtype dict:
    """
    work_shifts_path = Path(path_to_csv)

    with open(work_shifts_path) as file:
        work_shifts = csv.DictReader(file)
        hourly_cost = {}
        # initialise hourly_cost
        for hour in range(0, 24):
            hourly_cost[hour_to_time(hour)] = 0
        # for each row in work_shifts...           
        for row in work_shifts:
            # ... calculate the time_worked each hour...
            hourly_time_worked_dict = hourly_time_worked(row)
            for hour, time_worked in hourly_time_worked_dict.items():
                # ...and then update each hour's cost
                hourly_cost[hour_to_time(hour)] += time_worked*float(
                    row['pay_rate'])

    return hourly_cost


def process_sales(path_to_csv):
    """

    :param path_to_csv: The path to the transactions.csv
    :type string:
    :return: A dictionary with time (string) with format %H:%M as key and
    sales as value (string),
    and corresponding value with format %H:%M (e.g. "18:00"),
    and type float)
    For example, it should be something like :
    {
        "17:00": 250,
        "22:00": 0,
    },
    This means, for the hour beginning at 17:00, the sales were 250 dollars
    and for the hour beginning at 22:00, the sales were 0.

    :rtype dict:
    """
    sales_transactions_path = Path(path_to_csv)

    with open(sales_transactions_path) as file:
        sales_transactions = csv.DictReader(file)
        count = 0
        # hourly_sales will be the output dictionary.
        hourly_sales = {}
        # Initialise each hour in hourly_sales.
        for hour in range(0, 24):
            hourly_sales[hour_to_time(hour)] = 0  
        sales_tally = 0.00
        # Iterate through rows in sales_transactions table.
        for row in sales_transactions:
            if count == 0:
                # Fudge previous_row_hour for first row.
                previous_row_hour = hour_and_minute(row['time'])[0]
            current_row_hour = hour_and_minute(row['time'])[0]
            if current_row_hour == previous_row_hour:
                # Hour has not changed: accumulate sales.
                sales_tally += float(row['amount'])
            else:
                # Hour has incremented: update sales record for
                # previous hour.
                previous_hour_as_time = hour_to_time(previous_row_hour)
                # Store previous hour's final sales tally in
                # hourly_sales.
                hourly_sales[previous_hour_as_time] += sales_tally
                # Reset sales tally to start accumulating for new
                # hour.
                sales_tally = float(row['amount'])
            # Update previous_row_hour.
            previous_row_hour = current_row_hour
            # Update count.
            count += 1
        hour_as_time = hour_to_time(previous_row_hour)
        # Last hour's tally was missed so include it in
        # hourly_sales.           
        hourly_sales[hour_as_time] = sales_tally
                       
    return hourly_sales


def compute_percentage(shifts, sales):
    """

    :param shifts:
    :type shifts: dict
    :param sales:
    :type sales: dict
    :return: A dictionary with time as key (string) with format %H:%M and
    percentage of labour cost per sales as value (float),
    If the sales are null, then return -cost instead of percentage
    For example, it should be something like :
    {
        "17:00": 20,
        "22:00": -40,
    }
    :rtype: dict
    """
    percentages = {}
    for hour in range(0,24):
        # Convert hour into time format.
        hour_as_time = hour_to_time(hour)
        if sales[hour_as_time] == 0 or (sales[hour_as_time] is None):
            # If the sales are null (or zero), then percentage is -cost.
            percentages[hour_as_time] = -shifts[hour_as_time]
        else:
            # Otherwise calculate percentage in the normal way.
            percentages[hour_as_time] = \
            (shifts[hour_as_time]/sales[hour_as_time])*100

    return percentages


def best_and_worst_hour(percentages):
    """

    Args:
    percentages: output of compute_percentage
    Return: list of strings, the first element should be the best hour,
    the second (and last) element should be the worst hour. Hour are
    represented by string with format %H:%M
    e.g. ["18:00", "20:00"]

    """

    # Assumption: percentage = 0 implies zero cost and zero sales
    # (as it would be impossible to make any sales with no workers).

    # Assumption: percentage = 0 will be counted as equivalent to 100%.

    # Assumption: if there is a tie, any hour within the tied set may
    # be picked as representative.

    # Assumption: for the hours where cost is non-zero and sales is
    # zero (and therefore percentage is negative), the "worst" hour is
    # the one for which percentage is lowest (most negative).

    # Assumption: for the hours where cost and sales are non-zero,
    # the "best" hour is the one for which percentage is lowest.

    # Hours will be divided into three sets:

    # "negatives", where cost > 0 and sales = 0
    negatives = {hour:percentage for hour,
        percentage in percentages.items() if percentage < 0}

    # "positives", where cost > 0 and sales > 0
    positives = {hour:percentage for hour,
        percentage in percentages.items() if percentage > 0}

    # "zeroes", where cost = 0 and sales = 0
    zeroes = {hour:percentage for hour,
        percentage in percentages.items() if percentage == 0}
    
    # Pick a zero-percentage hour at random, push it into positives
    # dictionary and recalibrate its percentage to 100%.
    if zeroes is not None:
        zero_hour_percentage = zeroes.popitem()
        # Rename positives as it will now include
        # a zero-percentage hour.
        non_negatives = positives
        non_negatives[zero_hour_percentage[0]] = 100

    # Computing best:
    if  non_negatives is not None:
        best = min(non_negatives.items(), key=operator.itemgetter(1))[0]
    else:
        best = max(negatives.items(), key=operator.itemgetter(1))[0]

    # Computing worst:
    if  negatives is not None:
        worst = min(negatives.items(), key=operator.itemgetter(1))[0]
    else:
        worst = max(non_negatives.items(), key=operator.itemgetter(1))[0]

    return [best, worst]


def main(path_to_shifts, path_to_sales):
    """
    Do not touch this function, but you can look at it, to have an idea of
    how your data should interact with each other
    """

    shifts_processed = process_shifts(path_to_shifts)
    pprint(shifts_processed)
    sales_processed = process_sales(path_to_sales)
    pprint(sales_processed)
    percentages = compute_percentage(shifts_processed, sales_processed)
    pprint(percentages)
    best_hour, worst_hour = best_and_worst_hour(percentages)

    return best_hour, worst_hour



# path_to_sales = \
# r'C:\Users\jonpu\Desktop\Tenzo Python Challenge\transactions.csv'
# path_to_shifts = \
# r'C:\Users\jonpu\Desktop\Tenzo Python Challenge\work_shifts.csv'
# print (main(path_to_shifts, path_to_sales))

# Please write your name here: Jonathan Puddicombe