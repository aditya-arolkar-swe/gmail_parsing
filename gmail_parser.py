import argparse
import logging
import ssl
import time
from http.client import IncompleteRead
import tqdm
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import RequestException
from os_utils import create_folder_if_not_exists, read_file, write_file

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
MESSAGES_FILE = 'messages.pickle'
SENDER_COUNTS_FILE = 'senders_count/senders_count.pickle'
TOKEN_FILE = 'token.pickle'
MAX_RETRIES = 5
RETRY_BACKOFF_FACTOR = 2
MAX_WORKERS = 6
PORT = 8080
DEFAULT_TOP_SENDERS = 20


def authenticate_gmail():
    creds = read_file(TOKEN_FILE, logger)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=PORT)
        write_file(creds, TOKEN_FILE, logger)

    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    return service


def fetch_message(service, message_id, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            msg = service.users().messages().get(userId='me', id=message_id, format='metadata').execute()
            headers = msg['payload'].get('headers', [])
            for header in headers:
                if header['name'] == 'From':
                    sender = header['value']
                    sender_email = sender.split('<')[-1].strip('>')
                    return sender_email
        except (RequestException, ssl.SSLError, IncompleteRead, ssl.SSLError) as e:
            logger.error(f"Failed to fetch message {message_id}: {e}. Attempt {attempt + 1} of {retries}. Retrying...")
            time.sleep(RETRY_BACKOFF_FACTOR ** attempt)
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}.")
            break
    return None


def process_messages(service, messages, senders_count, multithreaded: bool = False):
    if multithreaded:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_message, service, message['id']): message['id'] for message in messages}
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    sender_email = future.result()
                    if sender_email:
                        senders_count[sender_email] += 1
                    if i % 100 == 0:
                        logger.info(f"Processed {i}/{len(messages)} messages...")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    else:
        message_count = 0
        for message in tqdm.tqdm(messages):
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg['payload'].get('headers', [])
            for header in headers:
                if header['name'] == 'From':
                    sender = header['value']
                    # Extract the email address only (remove the name part)
                    sender_email = sender.split('<')[-1].strip('>')
                    senders_count[sender_email] += 1
                    break
            message_count += 1
            if message_count % 1000 == 0:
                print(f"Processed {message_count}/{len(messages)} messages...")


def get_email_senders(service, multithreaded: bool = False, len_process: int = 10000, use_cache: bool = True):
    senders_count = defaultdict(int)
    messages = read_file(MESSAGES_FILE, logger)

    if not messages or not use_cache:
        logger.info("Fetching messages from Gmail API...")
        try:
            results = service.users().messages().list(userId='me').execute()
            messages.extend(results.get('messages', []))

            while 'nextPageToken' in results:
                page_token = results['nextPageToken']
                results = service.users().messages().list(userId='me', pageToken=page_token).execute()
                messages.extend(results.get('messages', []))
                if len(messages) % 2500 == 0:
                    logger.info(f"Fetched {len(messages)} messages...")

            logger.info(f"Found {len(messages)} total messages!")
            write_file(messages, MESSAGES_FILE, logger)

        except Exception as e:
            logger.error(f"Failed to fetch messages from Gmail API: {e}")
            return senders_count

    create_folder_if_not_exists('senders_count')
    for iter, i in enumerate(range(0, len(messages), len_process)):
        curr_dict = defaultdict(int)
        curr_file = f'senders_count/senders_count_{iter + 1}.pickle'
        cached_dict = read_file(curr_file, logger)

        if cached_dict:
            curr_dict.update(cached_dict)

        else:
            process_messages(service, messages[i:i+len_process], curr_dict, multithreaded=multithreaded)
            write_file(curr_dict, curr_file, logger)

        senders_count.update(curr_dict)

    return senders_count


def parse_args():
    parser = argparse.ArgumentParser(
        description='Parses your gmail inbox, and returns the top X 20 senders to your inbox')

    parser.add_argument('--no-cache', type=bool, default=False,
                        help='After first run, will store a cache and uses that by default for subsequent runs. '
                             'Use this flag to refresh your cache.')
    parser.add_argument('--top-n-senders', type=int, default=DEFAULT_TOP_SENDERS,
                        help=f'Number of senders to output. Default: {DEFAULT_TOP_SENDERS}')
    parser.add_argument('--multithreaded', type=bool, default=False,
                        help='Attempts to multithread the loading of messages. '
                             'Currently not working. Needs some work... ')

    return parser.parse_args()


def main():
    args = parse_args()
    service = authenticate_gmail()

    senders_count = read_file(SENDER_COUNTS_FILE, logger)

    if args.no_cache or not senders_count:
        senders_count = get_email_senders(service, multithreaded=args.multithreaded, use_cache=not args.no_cache)

        logger.info(f"Found {len(senders_count)} senders! Writing to local cache... ")
        write_file(senders_count, SENDER_COUNTS_FILE, logger)

    arr_counts = [(sender, count) for sender, count in senders_count.items()]
    arr_counts.sort(key=lambda x: x[1], reverse=True)
    print(f' - Top {args.top_n_senders} Senders to your Inbox - ')
    for email, count in arr_counts[:args.top_n_senders]:
        print(f'{email}: {count}')


if __name__ == '__main__':
    main()
