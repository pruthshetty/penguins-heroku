import os
import io
import sys
import time
import json
import openai
import requests
from PIL import Image
import streamlit as st
from streamlit_pills import pills
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
import itertools

def get_next_api_key(api_keys):
    for api_key in itertools.cycle(api_keys):
        yield api_key

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def load_resources():
    resources = {}
    resources['about_flexchat'] = read_file('flexchat_info/about_flexchat.txt')
    resources['system_prompt'] = read_file('flexchat_info/system_prompt.txt')
    resources['twilio_image'] = Image.open('flexchat_info/twilio_logo.ico')
    return resources

def get_pst_now():
    from datetime import datetime
    import pytz
    utc_now = datetime.now(pytz.utc)
    pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))
    return pst_now

def write_to_airtable(question, fb_option, pst_datetime):
    PERSONAL_ACCESS_TOKEN = st.secrets["artbl_access_token"]
    BASE_ID = st.secrets["artbl_base_id"]
    TABLE_NAME = 'FlexGPT'
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {PERSONAL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        'question': question,
        'response_helpful': fb_option,
        'datetime': pst_datetime
    }

    response = requests.post(url, headers=headers, data=json.dumps({"fields": data}))
    response_json = response.json()
    if 'id' in response_json:
        return response_json['id']
    return None

def write_to_airtable_demo(team_name, question, answer, pst_datetime):
    PERSONAL_ACCESS_TOKEN = st.secrets["artbl_access_token"]
    BASE_ID = st.secrets["artbl_base_id"]
    TABLE_NAME = 'FlexGPT_Demo'
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {PERSONAL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        'team_name': team_name,
        'question': question,
        'answer': answer,
        'datetime': pst_datetime
    }

    response = requests.post(url, headers=headers, data=json.dumps({"fields": data}))
    response_json = response.json()
    if 'id' in response_json:
        return response_json['id']
    return None

def init_environment():

    api_keys = [
    st.secrets["openai_api_key_1"],
    st.secrets["openai_api_key_2"],
    st.secrets["openai_api_key_3"],
    st.secrets["openai_api_key_4"],
    st.secrets["openai_api_key_5"],
    # st.secrets["openai_api_key_6"],
    # st.secrets["openai_api_key_7"],
    # st.secrets["openai_api_key_8"],
    # st.secrets["openai_api_key_9"],
    # st.secrets["openai_api_key_10"]
]
    api_key_generator = get_next_api_key(api_keys)
    api_key = next(api_key_generator)
    os.environ['OPENAI_API_KEY'] = api_key
    index_directory_path = "index_dir/"
    embeddings = OpenAIEmbeddings()
    faiss_db = FAISS.load_local("faiss_index", embeddings)
    return faiss_db

def gen_prompt(docs, query) -> str:
    return f"""
Context: {[doc.page_content for doc in docs[:2]]}
Question: {query}
Answer:
"""

def prompt(query):
    faiss_db = init_environment()
    docs = faiss_db.similarity_search(query)
    prompt = gen_prompt(docs, query)
    return prompt


def main():

    if 'res_flag' not in st.session_state:
        st.session_state['res_flag'] = False

    if 'fb_select' not in st.session_state:
        st.session_state.fb_select = None

    if 'result' not in st.session_state:
        st.session_state.result = ''
    
    model_val = 'gpt-4'
    resources = load_resources()
    st.set_page_config(page_title="FlexGPT", page_icon=resources['twilio_image'])

    # Add custom CSS styles
    custom_css = """
    <style>
        .result-text {
            font-size: 17px;
            line-height: 1.5;
        }
    </style>    """

    st.markdown(custom_css, unsafe_allow_html=True)

    #Sidebar

    st.sidebar.header("May the fourth be with you! 🌟")
    team_name = st.sidebar.text_input("Greetings, fellow spacefarer! What name do you go by in this vast galaxy?", "")
    resp_submit_btn = st.sidebar.button("Submit 💫", key="send_email_button", disabled=not st.session_state['res_flag'])
    
    fb_options = ['Yes', 'No']
    thumbs_list = ["👍", "👎"]

    st.title('FlexGPT')
    with st.expander("Who am I? 🤔"):
        st.caption(resources['about_flexchat'])

    
    user_input = st.text_area('Enter your question:', '')
    ask_btn = st.empty()
    st.markdown("<br>", unsafe_allow_html=True)
    res_box = st.empty()



    if st.session_state.result:
        res_box.write(f'{st.session_state.result}', unsafe_allow_html=True)
        

    result = ''
    if ask_btn.button("Ask ✨", type="primary") and len(user_input) > 0:
        report = []
        completion = openai.ChatCompletion.create(model="gpt-4", 
                                                 messages=[
              {"role": "system", "content": resources['system_prompt']},
              {"role": "user", "content": f"{prompt(user_input)}"},
              ], 
            stream=True, 
            max_tokens=512,
            temperature=0.1)

        for line in completion:
            if 'content' in line['choices'][0]['delta']:
                report.append(line['choices'][0]['delta']['content'])
            st.session_state.result = "".join(report).strip()
            res_box.write(f'{st.session_state.result}', unsafe_allow_html=True)
        pst_datetime = get_pst_now().strftime("%Y-%m-%d %H:%M:%S")
        record_id = write_to_airtable(user_input, "", pst_datetime)
        st.session_state['res_flag'] = True  # Add this line to update the 'res_flag'
        # st.write("---")
    st.session_state['res_flag'] = True
    if resp_submit_btn and len(team_name)>0 and st.session_state['res_flag']:
        pst_datetime = get_pst_now().strftime("%Y-%m-%d %H:%M:%S")
        record_id_demo = write_to_airtable_demo(team_name, user_input, st.session_state.result, pst_datetime)

if __name__ == "__main__":
    main()
