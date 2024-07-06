from collections import defaultdict

from simplegmail import Gmail

gmail = Gmail()
messages = gmail.get_messages(attachments='ignore')
senders_count = defaultdict(int)

for msg in messages:
	sender = msg.headers.get('From', None)
	# Extract the email address only (remove the name part)
	sender_email = sender.split('<')[-1].strip('>')
	senders_count[sender_email] += 1

print(f'Got {len(messages)} messages!')
