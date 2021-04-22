from csv import DictReader, DictWriter

def read_csv(filepath):
    """
    Takes a filepath string and returns a list with each row of the file as a dictionary as an entry in the list.
    
    Takes a relative, or absolute filepath as a string, opens the file, reads each row as a dictionary and adds the row/dictionary to a list and returns the list of rows as dictionary entries.

    Keyword arguments:
    filepath -- a string represetnation of an absolute or relative filepath
    """
    data = []
    with open(filepath, 'r', newline='\n') as csv_file:
        reader = DictReader(csv_file)
        for row in reader:
            data.append(row)

    return data

def write_csv(filepath, columns, data):
    """
    
    """
    with open(filepath, 'w', newline='\n') as csv_file:
        writer = DictWriter(csv_file, fieldnames=columns)
        
        writer.writeheader()

        writer.writerows(data)
    
    return "file written to {}".format(filepath)

def delete_row_from_csv(filepath, row_number):
    current_data = read_csv(filepath)
    print(current_data)
    # recreate current_data - row_number
    overwritten_data = []
    for i, order in enumerate(current_data):
        if(i != row_number):
            overwritten_data.append(order)
        # if(i == row_number):
        #     print("i: {}\nrow_number: {}\nrow: {}".format(i, row_number, order))
    write_csv(filepath, overwritten_data[0].keys(), overwritten_data)


def write_row_to_csv(filepath, row):
    with open(filepath, 'a', newline='\n') as csv_file:
        DictWriter(csv_file, fieldnames=row.keys()).writerow(row)

    return "row added to {}".format(filepath)

def delete_row(row_number):
    print("about to delete: {}\nfrom: {}".format(row_number, 'reports/pending_orders/buy_orders.csv'))
    delete_row_from_csv('reports/pending_orders/buy_orders.csv', row_number)

def delete_rows(row_numbers):
    print("about to delete: {}".format(row_numbers))
    for row_number in row_numbers:
        delete_row(row_number)