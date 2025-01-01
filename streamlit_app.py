import streamlit as st
import os
from openai import OpenAI
import pandas as pd
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from streamlit_chromadb_connection.chromadb_connection import ChromadbConnection
import chromadb
import boto3
from io import BytesIO
from dotenv import load_dotenv
import docx2txt

if 'email_data' not in st.session_state:
    st.session_state.email_data = None

if 'collection_name' not in st.session_state:
    st.session_state.collection_name = "email_collection"

if 'chroma_client' not in st.session_state:
    st.session_state.chroma_client = chromadb.PersistentClient('./chromaclient/')

if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = os.getenv("OPENAI_KEY")

#strip non body text from emails
def strip_emails(emails):
    # Create an OpenAI client.
    client = OpenAI(api_key=st.session_state.openai_api_key)
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

def st_vectorize(emails):
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
        collection_name=collection_name,
        embedding_function_name= "DefaultEmbeddingFunction"
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
    print("Vector DB Created")

def vectorize(emails):
    #Add body text of emails to vector db
    chroma_client = chromadb.PersistentClient('./chromaclient/')
    collection_name = "email_collection"
    collection = chroma_client.create_collection(name=collection_name)
    ids = []
    i=0
    for email in emails:
        ids.append("id"+str(i))
        i+=1
    collection.add(
    documents = emails,
    ids=ids
    )
    print("Vector DB Created")

def find_docs(search_string):
    collection = st.session_state.chroma_client.get_collection(name=st.session_state.collection_name)
    results = collection.query(
    query_texts=[search_string], # Chroma will embed this for you
    n_results=1 # how many results to return
    )
    print(results)
    return results['documents'][0][0]

def draft_email(email_string, context):
    client = OpenAI(api_key=st.session_state.openai_api_key)
    #key details prompt
    details_prompt = f"You are a communications consultant working for a bank. You are using a previously sent sample email from a previous project as a template for writing a similar email. Use the following sample email to extract all of the important pieces of information communicated to the customer. Sample email: {email_string}"
    #tone prompt
    tone_prompt = f"You are a communications consultant working for a bank. You are using a previously sent sample email from a previous project as a template for writing a similar email. Use the following sample email to determine the tone to use in the new email. Describe the tone in one descriptive sentence. Sample email: {email_string}"
    #sample key details retrieval
    messages=[
        {"role": "developer", "content": details_prompt}
        ]
    # Use OpenAI's API to generate a response
    response = client.chat.completions.create(
        model="gpt-4o",  # Use GPT-4 model
        messages=messages,
        temperature=0.7,  # Control randomness in responses
        n=1,  # Number of completions
        stop=None,  # Let the model decide when to stop
    )
    key_details = response.choices[0].message.content
    print(key_details)
    #sample tone retrieval
    messages=[
        {"role": "developer", "content": tone_prompt}
        ]
    # Use OpenAI's API to generate a response
    response = client.chat.completions.create(
        model="gpt-4o",  # Use GPT-4 model
        messages=messages,
        temperature=0.7,  # Control randomness in responses
        n=1,  # Number of completions
        stop=None,  # Let the model decide when to stop
    )
    tone = response.choices[0].message.content
    print(tone)
    prompt = f"You are a communications consultant working for a bank called BMO that has recently acquired Bank of the West. Draft the body of an email the bank is sending to its customers using the provided key copy points, details to include, and tone. The details to include and tone information come from a previous email about a similar subject, while the key copy points are specific to this project. The information in the key copy points should take precedence. Do not include any salutations, only draft the body of the email. \n Key Copy Points: {context}.\n Details to Include: {key_details}\n Tone to Use: {tone}"
    messages=[
    {"role": "developer", "content": prompt}
    ]
    # Use OpenAI's API to generate a response
    response = client.chat.completions.create(
        model="gpt-4o",  # Use GPT-4 model
        messages=messages,
        temperature=0.7,  # Control randomness in responses
        n=1,  # Number of completions
        stop=None,  # Let the model decide when to stop
    )

    # Extract and return the generated email text
    return response.choices[0].message.content

# Create S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


# Show title and description.
st.title("📄 Email Drafting")
st.write(
    "Upload a tactical communications plan below and pick which email from the plan you would like to draft! "
)

if st.button("Get Data"):
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
    body_text = strip_emails(emails)
    st.session_state.email_data = body_text
    print("Session State Set!")

if st.button("Create Vector DB"):
    if st.session_state.email_data is not None:
        vectorize(st.session_state.email_data)

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
            "Edit the key copy points to include",
            value=value,
            placeholder="Can you give me a short summary?",
            disabled=not uploaded_file,
        )
        sample_email = find_docs(value)
        if st.button("Draft Email"):
            draft = draft_email(sample_email, value)
            st.write(draft)
