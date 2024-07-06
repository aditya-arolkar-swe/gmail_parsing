import os
import pickle
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
MESSAGES_FILE = 'messages.pickle'
SENDER_COUNTS_FILE = 'sender_counts.pickle'
MAX_RETRIES = 5
RETRY_BACKOFF_FACTOR = 2
MAX_WORKERS = 6
PORT = 8080


def authenticate_gmail():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=PORT)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
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


def get_email_senders(service, multithreaded: bool = False, len_process: int = 10000):
    senders_count = defaultdict(int)
    messages = []

    if os.path.exists(MESSAGES_FILE):
        logger.info("Loading messages from local file...")
        try:
            with open(MESSAGES_FILE, 'rb') as f:
                messages = pickle.load(f)
            logger.info(f"Loaded {len(messages)} messages from local file.")
        except Exception as e:
            logger.error(f"Failed to load messages from file: {e}")
            return senders_count
    else:
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

            logger.info("Saving messages to local file...")
            with open(MESSAGES_FILE, 'wb') as f:
                pickle.dump(messages, f)
            logger.info(f"Saved {len(messages)} messages to local file.")
        except Exception as e:
            logger.error(f"Failed to fetch messages from Gmail API: {e}")
            return senders_count

    for iter, i in enumerate(range(0, len(messages), len_process)):
        curr_dict = defaultdict(int)
        curr_file = f'senders_count_{iter+1}.pickle'
        if os.path.exists(curr_file):
            with open(curr_file, 'rb') as f:
                curr_dict = pickle.load(f)

            print(f'Loaded {curr_file} from cache!')

        else:
            process_messages(service, messages[i:i+len_process], curr_dict, multithreaded=multithreaded)
            with open(curr_file, 'wb') as f:
                pickle.dump(curr_dict, f)

            print(f'Created {curr_file} and saved to {os.path.join(os.path.curdir, curr_file)}!')

        senders_count.update(curr_dict)

    return senders_count


def main():
    service = authenticate_gmail()

    if os.path.exists(SENDER_COUNTS_FILE):
        logger.info("Loading messages from local file...")
        with open(SENDER_COUNTS_FILE, 'rb') as f:
                senders_count = pickle.load(f)
    else:
        senders_count = get_email_senders(service)
        with open(SENDER_COUNTS_FILE, 'wb') as f:
            pickle.dump(senders_count, f)
        logger.info(f"Saved {len(senders_count)} sender counts to local file.")

    arr_counts = [(sender, count) for sender, count in senders_count.items()]
    arr_counts.sort(key=lambda x: x[1], reverse=True)
    for row in arr_counts[:20]:
        print(row)


if __name__ == '__main__':
    main()
