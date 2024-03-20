import streamlit as st
import spacy
from pdfminer.high_level import extract_text
from datetime import datetime
from dateutil import parser
from dateutil import relativedelta
import pandas as pd
import re
from tempfile import NamedTemporaryFile
import os
import json
import requests
from io import BytesIO
from spire.doc import *
from spire.doc.common import *
import google.generativeai as genai

doc = Document()

role = ''
department = ''
years_of_experience = 0
min_qualification = ''
keywords = []
list_of_score = {}
jd_done = False

st.set_page_config(page_title="Addverb Resume Shortlister", page_icon="https://addverb.com/wp-content/uploads/2023/12/cropped-MicrosoftTeams-image-7.png", layout="centered")

genai.configure(api_key="AIzaSyBrRVRj1I1lDwCRcMz9svDqAqa9TMo9Aw0")

generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}
safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]
model = genai.GenerativeModel(model_name="gemini-1.0-pro",
                              generation_config=generation_config,
                              safety_settings=safety_settings)
convo = model.start_chat(history=[
])



# -------------------------------------------------------------------- functions --------------------------------------------------------------------

def convert_pdf_to_text(pdf_path):
    text = extract_text(pdf_path)
    return text

def extract_text_from_docx(docx_path):
    doc.LoadFromFile(docx_path)
    section = doc.GetText()
    return section

def extract_text_from_doc(doc_path):
    doc.LoadFromFile(doc_path)
    section = doc.GetText()
    return section

def extract_text_after_keyword(text, keyword):
    pattern = re.compile(f'{re.escape(keyword)}\s*([\s\S]*?)(?:\n|$)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    else:
        return None


def extract_minimum_experience(text):
    min_ex_pattern = re.compile(r'\d\s?(?:-|to)\s?\d\s(?:years|Years)', re.IGNORECASE)    

    matches = min_ex_pattern.findall(text)
    return matches


def extract_content_between_keywords(text, keyword1, keyword2):
    pattern = re.compile(f'{re.escape(keyword1)}(.*?){re.escape(keyword2)}', re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    else:
        return None


def extract_technical_keywords(paragraph):
    nlp = spacy.load("en_core_web_sm")

    doc = nlp(paragraph)

    filler_words = ['comprehensive', 'knowledge', 'expertise', 'must', 'prior', 'experience',
                    'basic', 'understanding', 'of', 'is', 'a', 'and', 'in', 'new', '\n\n', ' \n\n', ' \n']

    technical_keywords = [token.text.lower() for token in doc
                          if token.text.lower() not in filler_words
                          and not token.is_punct
                          and len(token.text) > 1
                          and not token.text.isdigit()]

    return technical_keywords

def extract_date_ranges(text):
    date_range_pattern = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2})\s?(?:-|–|to|till|until)\s?(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2}))?\b', re.IGNORECASE)    

    matches = date_range_pattern.findall(text)
    return matches

def convert_two_digit_year(date_string):
    if(date_string.lower()=='present'):
        return 'present'

    date_string = date_string.replace("'", " ")
    date_string = date_string.replace('’', " ")   
    month_str, year_str = date_string.split(" ")
    if(len(year_str) == 2):
        return month_str + " " + f'20{year_str}'
    else:
        return date_string
    
def calculate_month_difference(start_date_str, end_date_str):
    if end_date_str.lower() == 'present':
        end_date_str = datetime.now().strftime("%b %Y")

    start_date = parser.parse(start_date_str)
    end_date = parser.parse(end_date_str)

    delta = relativedelta.relativedelta(end_date, start_date)
    months_difference = delta.years * 12 + delta.months

    return months_difference

# Score or percentage extraction
flag = 1    
# def extract_scores(text):
#     score_pattern = re.compile(r'\d?\d\.\d?\d')
#     matches = score_pattern.findall(text)

#     return matches

def extract_percentages(text):
    percentage_pattern = re.compile(r'\d\d%|\d\d\.\d\d%')

    matches = percentage_pattern.findall(text)

    return matches


def check_words_in_pdf(text_content, words_to_check):
    word_count = {word: text_content.lower().count(word.lower()) for word in words_to_check}
    return word_count

def get_similarity_score(job_responsibilities, text_content):
    content = '''These are the job responsibilities for a role - {job_responsibilities}  
                            This is the text extracted from the resume of a candidate - {text_content}
    Compare the job description and the data extracted from the resume and check if the candidate is a good fit for the role by comparing the job description and resume data. Just give me a similarity score \
        out of 10. But keep the marking parameters consistent, so that every time the same paragraph comes up, it should have the same score.Don't send anything else, just say Similarity score out of 10'''
    
    formatted_text = content.format(
    job_responsibilities=job_responsibilities,
    text_content=text_content
    )   
    
    try:
        convo.send_message(formatted_text)
        print("texxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxt =========== " + convo.last.text)
        desired_text = convo.last.text
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        desired_text = "Internal Server Error, cannot reach AI servers"

    print(desired_text)

    import re
    match = re.search(r'\b\d+\b', desired_text)

    if match:
        first_number = int(match.group())
        st.write("Similarity Score - ", first_number)
        print(first_number)
        return first_number
    else:
        print("No number found in the text")
        return 5
    
def extract_scores(text_content):
    content =  '''
                            This is the text extracted from the resume of a candidate - {text_content}
                            Find out if the candidate has mentioned his scores/percentage/marks in graduation, post graduation, school 10th or 12th class. If you find the score or percentage
                            give it in a list like this - 89%, 81.7%, 9.87. If not found just write - "Not Found"
                            '''

    formatted_text = content.format(
        text_content=text_content
    )

    try:
        convo.send_message(formatted_text)
        print("scorreeeeeeeeeeeeeeeeeeessssssssssssssssssssss =========== " + convo.last.text)
        desired_text = convo.last.text
    except requests.exceptions.RequestException as e:
        # print(f"Error: {e}")
        print("Internal Server Error, can't reach AI servers")
        desired_text = "Internal Server Error, can't reach AI servers"
    
    print(desired_text)

    pattern = re.compile(r'[-]?\d+(\.\d+)?')
    matches = pattern.finditer(desired_text)
    numbers = [float(match.group()) for match in matches if match.group()]
    print(numbers)
    st.write("Scores Found - ", numbers)
    number_flag = True
    for number in numbers:
        if(number <= 10):
            if(number < 6):
                number_flag = False
        elif(number<100 and number<60):
            number_flag = False

    if(number_flag):
        return 1
    else:
        return 0


def runningmain(text_content, file_name, text):
    total_score = 0
    dicc ={}

    date_ranges = extract_date_ranges(text_content)

    less_month_cnt = 0
    new_job_start_date = None
    previous_job_end_date = None
    gaps = 0
    total_months = 0

    for date_range in date_ranges:
        date_range = date_range.replace('to', '-')
        date_range = date_range.replace('till', '-')
        date_range = date_range.replace('until', '-')
        date_range = date_range.replace('–', '-')
        # print(date_range)

        start_date, end_date = [date.strip() for date in date_range.split('-')]

        start_date = convert_two_digit_year(start_date)
        # st.write("Job Starting Date - ", start_date)
        print(start_date)
        end_date = convert_two_digit_year(end_date)
        # st.write("Job Ending Date - ", end_date)
        print(end_date)
        months_difference = calculate_month_difference(start_date, end_date)
        total_months = total_months + months_difference
        
        if months_difference is not None:
            if months_difference < 12:
                less_month_cnt += 1
            print(f"Time between {start_date} and {end_date}: {months_difference} months")
            # st.write(f"Time between {start_date} and {end_date}: {months_difference} months")

            if new_job_start_date:
                previous_job_end_date = end_date
                if previous_job_end_date == 'present':
                    new_job_start_date = start_date
                    previous_job_end_date = None
                else:
                    print("prev_job_end_date = ", previous_job_end_date)
                    # st.write("prev_job_end_date = ", previous_job_end_date)
                    print("new_job_Start_date = ", new_job_start_date)
                    # st.write("new_job_Start_date = ", new_job_start_date)
                    gap_months = calculate_month_difference(new_job_start_date, previous_job_end_date)
                    print("gaaap - ", gap_months)
                    # st.write("gap - ", gap_months)
                    if(gap_months < -3):
                        gaps = gaps+1
                    new_job_start_date = start_date
                    previous_job_end_date = None
            else:
                new_job_start_date = start_date 
                print("new_job_Start_date = ", new_job_start_date)
                # st.write("new_job_Start_date = ", new_job_start_date)
                print("prev_job_end_date = ", previous_job_end_date)
                # st.write("prev_job_end_date = ", previous_job_end_date)


        else:
            print(f"Currently employed from {start_date}")
            # st.write(f"Currently employed from {start_date}")
            previous_job_end_date = None

    if(less_month_cnt < 2):
        total_score = total_score + 10
        print("total score after job duration - " + str(total_score))
        st.write(f"**Candidate hasn't switched jobs before completing 12 months of tenure**")
        st.write(f":red[Score till now] - **({str(total_score)}/50)**")
        dicc.update({"Job Switches":"PASS"})
    else:
        total_score = total_score + 1
        print("leaving orgs early")
        st.write("**Candidate has switched jobs before completing 12 months of tenure**")
        dicc.update({"Job Switches":"FAIL"})

    print("total Months = ", total_months)
    # st.write("total experience = ", total_months/12)
    if(total_months/12 < minimum_exp):
        print("Minimum Experience Criteria Doesn't matcjh")
        st.write("***:red[MINIMUM EXPERIENCE CRITERIA DOESN'T MATCH]***")
        total_score = -100
        dicc.update({"Experience":"MINIMUM EXPERIENCE CRITERIA DOESN'T MATCH"})
    else:
        dicc.update({"Experience":"PASS"})

    if(gaps < 2):
        total_score = total_score + 10
        print("total score after career breaks - " + str(total_score))
        st.write(f"**Candidate doesn't have two career breaks more than 3 months**")
        st.write(f":red[Score till now] - **({str(total_score)}/50)**")
        dicc.update({"Career Breaks":"PASS"})
    else:
        total_score = total_score + 1
        print("having more than one 3 month career break")
        st.write(f"**Candidate has more than one career break of 3 months each**")
        st.write(f":red[Score till now] - **({str(total_score)}/50)**")
        dicc.update({"Career Breaks":"FAIL"})



    # Score or percentage extraction
    # flag = 1    

    # scores = extract_scores(text_content)
    # percentages = extract_percentages(text_content)
    # print("Extracted Scores:")
    # st.write("Extracted Scores:")
    # for score in scores:
    #     st.write(score)
    #     print(score)
    #     if(float(score) < 10 and float(score) < 6 and float(score) > 4):
    #         flag = 0
    #         print("below par score")
    #         st.write("below par score")

    # print("Extracted Percentages")
    # st.write("Extracted Percentages")
    # for percentage in percentages:
    #     st.write(percentage)
    #     print(percentage)
    #     percentage = percentage.replace("%", "")
    #     if(float(percentage) > 10 and float(percentage)  < 60 and float(percentage) > 40):
    #         flag = 0
    #         print("below par percentage")
    #         st.write("below par percentage")

    # if(flag):
    #     total_score = total_score + 10    
    # else:
    #     total_score = total_score + 2

    score = extract_scores(text_content)
    if(score == 1):
        total_score = total_score+10
        st.write(f"Candidate has academic scores in the acceptable range")
    else:
        st.write(f"Candidate has below par scores")
    
    st.write(f":red[Score after results extraction] - **({str(total_score)}/50)**")


    # keywords
    total_words = 0
    words_in_pdf = 0
    try:
        word_count_in_pdf = check_words_in_pdf(text_content, keywords)
        print("Word Count in PDF:")
        for word, count in word_count_in_pdf.items():
            total_words = total_words + 1
            if(count > 0):
                words_in_pdf = words_in_pdf + 1
            # print(f"{word}: {count} occurrences")

    except Exception as e:
        print(f"An error occurred: {e}")

    if(total_words > 0):
        print(words_in_pdf/total_words)
        st.write(f"Percentage of Keywords found in the resume: + {(words_in_pdf/total_words)*100}") 
        if(words_in_pdf/total_words >= 0.5):
            total_score = total_score + 10
    else:
        total_score = total_score + 3

    st.write(f":red[Score after keyword matching] - **({str(total_score)}/50)**")
    dicc.update({"Keyword Match Percentage":f"{(words_in_pdf/total_words)*100}"})


    # similarity score
    job_responsibilities = extract_content_between_keywords(text, 'Job Responsibilities', '1')
    similarity_score = get_similarity_score(job_responsibilities, text_content)
    total_score = total_score+similarity_score

    print("Total Score - " + str(total_score))
    st.write(f"Similarity between Job Responsibilities from JD and candidate's resume out of 10 - ({str(similarity_score)}/10)")
    st.write(f"**:red[Total Score of the Candidate]** - **({str(total_score)}/50)**")
    dicc.update({"Similarity Score":f"{str(similarity_score)}"})

    if(total_score > 30):
        st.write(f"***:red[SHORTLISTED]***")
        dicc.update({"RESULT":"SHORTLISTED"})
        # os.replace(file_path, folder_path + "/shortlisted/" + file_name)
    else:
        dicc.update({"RESULT":"FAILED"})
        
    dicc.update({"TOTAL SCORE":f"{total_score}"}) 

    list_of_score[file_name] = dicc


# -------------------------------------------------------------------- functions end--------------------------------------------------------------------
            
st.image("https://addverb.com/wp-content/uploads/2024/03/banner-full-.png")
uploaded_jd = st.file_uploader("Upload a Job Description", type=["pdf", "doc", "docx"])

if uploaded_jd is None:
    st.write("Please upload a Job Description")
else:
    file_extension = uploaded_jd.name.split(".")[-1].lower()
    pdf_bytes = uploaded_jd.read()
    if file_extension == "pdf":
        with NamedTemporaryFile(dir='.', suffix='.pdf') as f:
            f.write(uploaded_jd.getbuffer())
            text = convert_pdf_to_text(f.name)
    elif file_extension == "doc":
        with NamedTemporaryFile(dir='.', suffix='.doc') as f:
            f.write(uploaded_jd.getbuffer())
        text = extract_text_from_doc(f.name)
    elif file_extension == "docx":
        with NamedTemporaryFile(dir='.', suffix='.docx') as f:
            f.write(uploaded_jd.getbuffer())
        text = extract_text_from_docx(f.name)
    else:
        st.write(f"Unsupported file type: {file_extension}")

    # text = extract_text(uploaded_jd)
    role = extract_text_after_keyword(text, "Role")
    department = extract_text_after_keyword(text, "Department")
    min_ex = extract_minimum_experience(text)
    tech_skills_para = extract_content_between_keywords(text, 'Technical Skills Required', 'Behavioral Skills Required')
    keywords = extract_technical_keywords(tech_skills_para)

    print("Role - " + role)
    print("Department - " + department)
    print("Minimum Experience - ", min_ex)
    print(keywords)

    st.header(":red[Job Description Uploaded for : ]")
    st.write(f"Role - ***{role}***")
    st.write(f"Department - ***{department}***")
    st.write("Experience Required - ")
    for i in min_ex:
        st.markdown(f"-  + ***{i}***")
    pattern = re.compile(r'\b(\d+)\b')
    minimum_exp = int(pattern.search(min_ex[0]).group(1)) if pattern.search(min_ex[0]) else None
    print("minimum experience - ", minimum_exp)

    jd_done = True


if(jd_done):
    uploaded_resumes = st.file_uploader("Upload Resumes", type=["pdf", "doc", "docx"], accept_multiple_files=True)

    if(uploaded_resumes is not None):
        for uploaded_resume in uploaded_resumes:
            file_extension = uploaded_resume.name.split(".")[-1].lower()
            if file_extension == "pdf":
                with NamedTemporaryFile(dir='.', suffix='.pdf') as f:
                    f.write(uploaded_resume.getbuffer())
                    text_content = convert_pdf_to_text(f.name)
            elif file_extension == "doc":
                with NamedTemporaryFile(dir='.', suffix='.doc') as f:
                    f.write(uploaded_resume.getbuffer())
                    text_content = extract_text_from_doc(f.name)
            elif file_extension == "docx":
                with NamedTemporaryFile(dir='.', suffix='.docx') as f:
                    f.write(uploaded_resume.getbuffer())
                    text_content = extract_text_from_docx(f.name)
            else:
                st.write(f"Unsupported file type: {file_extension}")
                break
            
            print(f.name)
            st.write("--------------------")
            st.header(uploaded_resume.name)
            runningmain(text_content, uploaded_resume.name, text)

# import operator
# cd = sorted(list_of_score.items(),key=operator.itemgetter(1),reverse=True)
# # print(cd)
# print(*cd, sep = "\n")
# st.write(*cd, sep = "\n")

sorted_scores = sorted(list_of_score.items(), key=lambda x: x[1]['TOTAL SCORE'], reverse=True)

data = []
for file_name, attributes in sorted_scores:
    row = [file_name]
    row.extend(attributes.values())
    data.append(row)

df = pd.DataFrame(data, columns=["File Name", "Job Switch", "Experience", "Career Breaks", "Keyword Matching Percentage", "Similarity Score", "Result", "Total Score"])

excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)

import base64

excel_byte_stream = excel_buffer.getvalue()

excel_base64 = base64.b64encode(excel_byte_stream).decode()
download_link = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_base64}">Download Excel file</a>'

st.markdown(download_link, unsafe_allow_html=True)
                            


    
