For this script to work, you must first create an OAuth credentials JSON from your google cloud console. Instructions:

To create a Google API key and set it up to read your emails, you'll need to follow these steps:

    Set Up a Google Cloud Project:
        Go to the Google Cloud Console.
        Create a new project or select an existing project.
    
    Enable the Gmail API:
        In the Cloud Console, go to the API & Services > Library.
        Search for "Gmail API" and enable it for your project.
    
    Set Up OAuth 2.0 Credentials:
        Go to API & Services > Credentials.
        Click on Create Credentials and select OAuth client ID.
        Configure the consent screen if prompted:
            Fill out the required fields.
            Save and continue.
        Choose the application type (e.g., Web application).
        Add authorized redirect URIs (e.g., http://localhost if you're testing locally).
            Specifically, add "http://localhost/8080"
            You can also change this to another port at the top of gmail_parser.py by editing the "PORT" variable
        Click Create to generate your OAuth 2.0 Client ID and Client Secret.
        Download the credentials file, which will be in JSON format.
