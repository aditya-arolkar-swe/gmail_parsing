from simplegmail import Gmail

gmail = Gmail()
messages = gmail.get_messages(attachments='ignore')

print(f'Got {len(messages)} messages!')
