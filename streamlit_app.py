import streamlit as st
from openai import OpenAI
import pandas as pd

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
