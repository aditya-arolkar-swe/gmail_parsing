import logging
from collections import defaultdict
from simplegmail import Gmail
from os_utils import read_file, write_file

top_n_senders = 20
gmail = Gmail()
message_cache_filename = 'simple_parser_cache.pickle'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# grab messages
messages = read_file(message_cache_filename, logger)
if not messages:
	messages = gmail.get_messages(attachments='ignore')
	write_file(messages, message_cache_filename, logger)

logger.info(f'Got {len(messages)} messages!')

# count senders
senders_count = defaultdict(int)

for msg in messages:
	sender = msg.headers.get('From', None)
	# Extract the email address only (remove the name part)
	if sender is not None:
		sender_email = sender.split('<')[-1].strip('>')
		senders_count[sender_email] += 1

# sort senders
arr_counts = [(sender, count) for sender, count in senders_count.items()]
arr_counts.sort(key=lambda x: x[1], reverse=True)

# display top senders
print(f' - Top {top_n_senders} Senders to your Inbox - ')
for email, count in arr_counts[:top_n_senders]:
	print(f'{email}: {count}')
