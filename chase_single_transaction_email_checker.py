from __future__ import print_function
from os import read
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64, re

from oauthlib.oauth2.rfc6749.clients.base import BODY

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
    ]

def get_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def get_message_ids_by_query(query_string):
    service = get_service()
    message_results = service.users().messages().list(userId='me', q=query_string).execute()
    # print("message_results: {}".format(message_results))
    if(message_results['resultSizeEstimate'] == 0):
        return []
    return message_results['messages'] if message_results['messages'] is not None else []

def get_labels():
    service = get_service()
    labels = service.users().labels().list(userId="me").execute()
    # print(labels)
    labels_dict = {}
    for label in labels["labels"]:
        labels_dict[label["name"]] = label["id"]
    # print("labels_dict: {}".format(labels_dict))
    return labels_dict

def get_message(message_id):
    service = get_service()
    message = service.users().messages().get(userId='me', id=message_id).execute()
    return message

def extract_relevant_headers(headers):
    data = {}
    relevant_headers = [
        "From",
        "To",
        "Subject",
        "Date"
    ]
    for header in headers:
        if header['name'] in relevant_headers:
            data[header['name']] = header['value']

    return data

def decode_message_part(message_part):
    return base64.urlsafe_b64decode(message_part['body']['data']).decode().strip()

def extract_authorized_time(condensed_message):
    split_condensed_message = condensed_message.split('on ')
    if split_condensed_message[0][0:11] == 'A charge of':
        if len(split_condensed_message) > 1:
            return split_condensed_message[1]

def extract_amount(condensed_message):
    return re.search('\d+[.]\d+', condensed_message).group().strip()

def extract_vendor(condensed_message):
    # return re.search('[A-Z0-9]{4}[A-Z0-9-#*: ]{1,21}', condensed_message).group().strip() -> back when I thought all vendors must be capitalized, until I got data showing me it wasn't...
    split_message = condensed_message.split(' at ')
    split_vendor = split_message[1].split(' has ')
    vendor = split_vendor[0]
    # print("vendor: {}".format(vendor))
    return vendor

def extract_condensed_message(full_message):
    for message in full_message.split('.\r\n'):
        if message[0:11] == 'A charge of':
            return message

def message_to_dict(message):

    message_dict = {}

    # grab gmail message id & thread id
    message_dict["gmail_message_id"] = message['id']
    message_dict["gmail_thread_id"] = message['threadId']

    # grab relevant headers ["From", "To", "Subject", "Date"]
    for rhk, rhv in extract_relevant_headers(message['payload']['headers']).items():
        message_dict[rhk] = rhv

    # grab and decode the full message from the message payload
    message_dict["full_message"] = decode_message_part(message['payload'])

    # extract condensed message from full message
    message_dict["condensed_message"] = extract_condensed_message(message_dict["full_message"])
    # print("condensed_message: {}".format(message_dict["condensed_message"]))

    # extract vendor fromm condensed_message
    message_dict["vendor"] = extract_vendor(message_dict["condensed_message"])

    # extract amount from condensed_message
    message_dict["amount"] = extract_amount(message_dict["condensed_message"])

    # extract authorized_time from condensed_message
    message_dict["authorized_time"] = extract_authorized_time(message_dict["condensed_message"])

    return message_dict

def add_labels_to_message(message_dict, label_ids):
    service = get_service()
    service.users().messages().modify(userId="me", id=message_dict["gmail_message_id"], body={"addLabelIds": label_ids}).execute()

def remove_labels_from_message(message_dict, label_ids):
    service = get_service()
    service.users().messages().modify(userId="me", id=message_dict["gmail_message_id"], body={"removeLabelIds": label_ids}).execute()

def write_chase_transaction(message_dict):
    from csv_utils import write_row_to_csv
    write_dict = message_dict
    write_dict.pop("full_message")
    write_row_to_csv('chase_expenses.csv', write_dict)

def check_for_unread_inbox_single_chase_transactions():
    labels_dict = get_labels()

    messages = [get_message(message['id']) for message in get_message_ids_by_query('from:"chase" subject:"Single Transaction Alert" label:"INBOX" label:"UNREAD"')]

    print("found {} chase messages".format(len(messages)))

    for message in messages:
        message_dict = message_to_dict(message)

        print("condensed message: {}".format(message_dict["condensed_message"]))

        print("writing...")
        write_chase_transaction(message_dict)

        print("adding Auto-Finances/Chase and Auto-Finances/Recorded labels to message")
        add_labels_to_message(message_dict, [labels_dict["Auto-Finances/Chase"], labels_dict["Auto-Finances/Recorded"]])

        print("removing INBOX and UNREAD lables")
        remove_labels_from_message(message_dict, [labels_dict["INBOX"], labels_dict["UNREAD"]])

    print("{} messages recorded, labeled, and removed from INBOX & UNREAD".format(len(messages)))

def reset_chase_transactions():

    labels_dict = get_labels()

    messages = [get_message(message['id']) for message in get_message_ids_by_query('from:"chase" subject:"Single Transaction Alert"')]

    print("found {} chase messages".format(len(messages)))

    for message in messages:
        message_dict = message_to_dict(message)

        print("condensed_message: {}".format(message_dict["condensed_message"]))

        print("adding INBOX & UNREAD labels")
        add_labels_to_message(message_dict, [labels_dict["INBOX"], labels_dict["UNREAD"]]) 

        print("removing Auto-Finances/Chase & Auto-Finances/Recorded lables")
        remove_labels_from_message(message_dict, [labels_dict["Auto-Finances/Chase"], labels_dict["Auto-Finances/Recorded"]])

    print("{} TRANSACTIONS RESET".format(len(messages)))


if __name__ == '__main__':
    check_for_unread_inbox_single_chase_transactions()
    # reset_chase_transactions()

    # TODO: check against existing message_ids to make sure the message hasn't been already recorded

    # TODO: give this job to a raspberry pi that will run this script every 5 minutes

    # TODO: make the raspberry pi back up to S3 or somewhere else