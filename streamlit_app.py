import streamlit as st
import os
from openai import OpenAI
import pandas as pd
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from streamlit_chromadb_connection.chromadb_connection import ChromadbConnection
import boto3
from io import BytesIO
from dotenv import load_dotenv
import docx2txt

#strip non body text from emails
def strip_emails(emails, openai_api_key):
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)
    body_text_list = []
    for email in emails:
        messages=[
            {"role": "developer", "content": f"The following is the full text of an email extracted from a Word or PDF document, return only the body text of the email. Full Text: {email}"}
            ]
        # Use OpenAI's API to generate a response
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4 model
            messages=messages,
            temperature=0.7,  # Control randomness in responses
            n=1,  # Number of completions
            stop=None,  # Let the model decide when to stop
        )
        body_text = response.choices[0].message.content
        body_text_list.append(body_text)
    return body_text_list

def vectorize(emails):
    #Add body text of emails to vector db
    #collection = chroma_client.create_collection(name="test_collection")
    configuration = {
        "client": "PersistentClient",
        "path": "./chromaclient/"
    }
    collection_name = "test_collection"
    conn = st.connection("chromadb",
                        type=ChromadbConnection,
                        **configuration)
    conn.create_collection(
        collection_name=collection_name
    )
    ids = []
    i=0
    for email in emails:
        ids.append("id"+str(i))
        i+=1
        conn.upload_documents(
            collection_name=collection_name,
            documents = emails,
            ids=ids
        )

# Create S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


# Show title and description.
st.title("📄 Document question answering")
st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.text_input("OpenAI API Key", type="password")

if st.button("Get Data"):
    if openai_api_key:
        emails = []
        # Store bucket name
        bucket_name = "takhan-sample-email-bucket"

        # Store contents of bucket
        objects_list = s3.list_objects_v2(Bucket=bucket_name).get("Contents")

        # Iterate over every object in bucket
        for obj in objects_list:
            #print(obj)
            obj_name = obj["Key"]
            response = s3.get_object(Bucket=bucket_name, Key=obj_name)
            file_stream = BytesIO(response['Body'].read())
            text= docx2txt.process(file_stream)
            print(text)
            emails.append(text)
        body_text = strip_emails(emails, openai_api_key)
#if not openai_api_key:
    #st.info("Please add your OpenAI API key to continue.", icon="🗝️")
#else:

# Create an OpenAI client.
client = OpenAI(api_key=openai_api_key)


# Let the user upload a file via `st.file_uploader`.
uploaded_file = st.file_uploader(
    "Upload a document"
)
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, skiprows=1)
    filtered_df = df[(df['CHANNEL/TACTIC'] == 'Email') & (df['COMMUNICATION'].notna())]
    #print(filtered_df['KEY COPY POINTS'])

    option = st.selectbox("Which email do you want to generate?", filtered_df['COMMUNICATION'])
    if option is not None:
        value = filtered_df.loc[filtered_df['COMMUNICATION'] == option].iloc[0]['KEY COPY POINTS']
        print(value)
        # Ask the user to edit the email description via `st.text_area`.
        question = st.text_area(
            "Now ask a question about the document!",
            value=value,
            placeholder="Can you give me a short summary?",
            disabled=not uploaded_file,
        )
question = None
if uploaded_file and question:

    # Process the uploaded file and question.
    document = uploaded_file.read().decode()
    messages = [
        {
            "role": "user",
            "content": f"Here's a document: {document} \n\n---\n\n {question}",
        }
    ]

    # Generate an answer using the OpenAI API.
    #stream = client.chat.completions.create(
        #model="gpt-4o",
        #messages=messages,
        #stream=True,
    #)

    # Stream the response to the app using `st.write_stream`.
    #st.write_stream(stream)
