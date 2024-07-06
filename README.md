# Gmail Inbox Parsing

This is a simple python application that parses your gmail inbox and returns the email addresses that sent the most emails to you. I built this as a tool to help me clear out my inbox to meet the Berkeley mail 5 GB limit.  

I had noticed that most of my gmail space was not from large attachments but from repeated spam from the same sender over many years. Once you identify the emails with the most spam, you can delete all mail from them. In the gmail app you can do this by searching "from: {email}", then "select all conversations that match this search", then "delete". 

1. Install requirements

		pip3 install -r requirements.py

3. Create google oauth credentials (details below), and save json to project root directory

4. Run app

		python3 gmail_parser.py

## Credentials JSON creation:

To create a Google API key and set it up to read your emails, you'll need to follow these steps:

Set Up a Google Cloud Project:
 - Go to the Google Cloud Console.
 - Create a new project or select an existing project.

Enable the Gmail API:
 - In the Cloud Console, go to the API & Services > Library.
 - Search for "Gmail API" and enable it for your project.

Set Up OAuth 2.0 Credentials:
 - Go to API & Services > Credentials.
 - Click on Create Credentials and select OAuth client ID.
 - Configure the consent screen if prompted:
     - Fill out the required fields.
     - Save and continue.
 - Choose the application type (e.g., Web application).
 - Add authorized redirect URIs (e.g., http://localhost if you're testing locally).
     - Specifically, add "http://localhost/8080"
     - You can also change this to another port at the top of gmail_parser.py by editing the "PORT" variable
 - Click Create to generate your OAuth 2.0 Client ID and Client Secret.
 - Download the credentials file, which will be in JSON format.
 - Rename it to "credentials.json" and add to this directory
