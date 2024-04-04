import streamlit as st
import spacy
from pdfminer.high_level import extract_text
from datetime import datetime
from dateutil import parser
from dateutil import relativedelta
import pandas as pd
import re
from tempfile import NamedTemporaryFile
import json
import requests
from io import BytesIO
from spire.doc import *
from spire.doc.common import *
import google.generativeai as genai
from dateutil.relativedelta import relativedelta


doc = Document()

role = ''
department = ''
years_of_experience = 0
min_qualification = ''
keywords = []
list_of_score = {}
jd_done = False
current_date = datetime.now()

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


def month_to_num(month):
    try:
        return datetime.strptime(month, "%b").month
    except ValueError:
        # If the month string does not match the expected format,
        # try parsing it with a different format
        return datetime.strptime(month, "%B").month


def calculate_month_difference(start_date, end_date):
    if end_date.lower().strip() == 'present' or end_date.lower().strip() == 'till now' or end_date.lower().strip() == 'till today' or end_date.lower().strip() == 'today':
        end_datetime = current_date
        print("end - ", end_datetime)
    else:
        end_month, end_year = map(int, end_date.split('/'))
        end_datetime = datetime(end_year, end_month, 1)

    start_month, start_year = map(int, start_date.split('/'))

    start_datetime = datetime(start_year, start_month, 1)

    difference = relativedelta(end_datetime, start_datetime)
    return difference.years * 12 + difference.months

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

    filler_words = ['comprehensive', 'knowledge', 'expertise', 'must', 'prior', 'experience', 'able', 'etc', 'as', 'such', 'enable', 'other', 'skills', 'preferred', 'that', 
                    'basic', 'understanding', 'arise' ,'of', 'is', 'a', 'and', 'in', 'new', 'have', 'strong', 'able', 'to', 'the', 'contribute', 'developing', 'intelligent' , 'solutions',
                     'have', 'strong', 'of', 'enable', 'ability', 'contribute', 'will', 'be', 'going', 'to', '&', 'in', 'with', 'within', 'our', 'provide', 'you', 'propose', 
                     'skills' , 'Hands-on', 'experience' ,'\n\n', ' \n\n', ' \n']

    technical_keywords = [token.text.lower() for token in doc
                          if token.text.lower() not in filler_words
                          and not token.is_punct
                          and len(token.text) > 1
                          and not token.text.isdigit()]

    return technical_keywords

def extract_date_ranges(text):
    # date_range_pattern = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2})\s?(?:-|–|to|till|until)\s?(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2}))?\b', re.IGNORECASE)    
    date_range_pattern = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2})\s?(?:-|–|to|till|until)\s*(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\'?\’?\s?(?:\d{2,4}|\'\d{2}))?\b', re.IGNORECASE)

    matches = date_range_pattern.findall(text)
    print(matches)
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
    

# Score or percentage extraction
flag = 1    

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
    
def extract_scores(academic_scores):
    pattern = re.compile(r'[-]?\d+(\.\d+)?')
    xy = ','.join(academic_scores)
    print("xy ", xy)
    matches = pattern.finditer(xy)

    numbers = [float(match.group()) for match in matches if match.group()]
    print(numbers)
    # st.write("Scores Found - ", numbers)
    number_flag = True
    for number in numbers:
        if(number == 4.33):
            continue
        elif(number <= 10):
            if(number < 6 and number > 4.33):
                number_flag = False
            elif(number < 2.6):
                number_flag = False
        elif(number<100 and number<60):
            number_flag = False

    if(len(numbers) == 0):
        number_flag = False

    if(number_flag):
        return 1
    else:
        return 0

def extract_year_score(text_content):
    content =  ''' 
    This is the text extracted from the resume of a candidate - {text_content}
    Return a JSON with two fields which will be lists named all_dates and academic_scores. The first field will contain list of date ranges. In all_dates, the list will contain all the date ranges mentioned by the candidate where they have worked in an organization as a full time employee(not internships) and the duration of their education, for example if someone has mentioned that the duration of their work in organization ABC was from May 2020 to Jan 2021, add it to the list as 5/2020 - 1/2021. 
    If they have mentioned that they had their graduation from 2020-2024 add it to the second list as 5/2020-5/2024. If no month is mentioned in the date range automatically add the month as 5. Follow the same format for all the date ranges in the first and second list "staring month in digits/starting year in digits - ending month in digits/ending year in digits". Only add work date ranges and education date ranges and to differentiate between them add a "w" in brackets at the end of job work ranges.
    The second list named academic_scores should be the list of academic scores found in the resume of the candidate, percentage or cgpa of graduation, post graduation or school
    if the candidate has mention 9.8 or 98.2%, send me a list of scores as 9.8, 98.2          
    Please be consistent with this, so that everytime the same text content comes same dates should appear.
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

    return desired_text


def runningmain(text_content, file_name, text):
    total_score = 0
    dicc ={}
    less_than_12 = 0
    total_experience = 0

    desired_text = extract_year_score(text_content)

    desired_text = desired_text.replace("```", "")
    desired_text = desired_text.replace("json", "")
    desired_text = desired_text.replace("```", "")
    desired_text = desired_text.replace("JSON", "")

    response_data = json.loads(desired_text)

    json_date_ranges = response_data.get('all_dates', [])
    academic_scores = response_data.get('academic_scores', [])

    duration_list = []
    total_experience = 0

    def normalize_year(year):
        print(year)
        if('w' in year or 'W' in year):
            year = year.split('(')[0].strip()
            if year.lower() == "present":
                current_date = datetime.now()
                year = str(current_date.year) 
            elif len(year) == 2:
                if int(year) >= 50:  
                    year = "19" + year 
                else:
                    year = "20" + year 
            year = year + '(w)'
        else:
            if year.lower() == "present":
                current_date = datetime.now()
                year = str(current_date.year)
            elif len(year) == 2:
                if int(year) >= 50:  
                    year = "19" + year
                else:
                    year = "20" + year
        return year

    date_ranges = []
    for date_range in json_date_ranges:
        try:
            start_date, end_date = date_range.split(' - ')
        except Exception as e:
            start_date = date_range.split('(')[0].strip()
            end_date = date_range
    
        try:
            start_month, start_year = start_date.split('/')
        except Exception as e:
            start_month = 5
            start_year = start_date
        if('present' in end_date.lower()):
            end_month = current_date.month
            end_year = str(current_date.year) + "(w)"
        else:
            try:
                end_month, end_year = end_date.split('/')
            except Exception as e:
                end_month = 5
                end_year = end_date
        start_year = normalize_year(start_year)
        end_year = normalize_year(end_year)  
        date_ranges.append((f"{start_month}/{start_year} - {end_month}/{end_year}"))
    print(date_ranges)


    for date_range in date_ranges:
        start_date, end_date = date_range.split(' - ')
        if '(w)' in end_date:
            end_date = end_date.split('(')[0].strip() 
            print("end date ", end_date)
            months_difference = calculate_month_difference(start_date, end_date)
            print(months_difference)
            if(months_difference<12):
                less_than_12 += 1
            total_experience += months_difference

        duration_list.append((start_date, end_date))


    sorted_date_ranges = sorted(duration_list, key=lambda x: datetime.strptime(x[0], "%m/%Y"), reverse=True)

    for date in sorted_date_ranges:
        print(date)

    gaps = 0
    for i in range(0, len(sorted_date_ranges)):
        if(i+1 < len(sorted_date_ranges)):
            previous_end_date = sorted_date_ranges[i+1][1]
            start_date = sorted_date_ranges[i][0]
            gap_months = calculate_month_difference(start_date, previous_end_date)
            print("gapp ", gap_months)
            if gap_months > 3:
                gaps += 1
    
    if(len(date_ranges) == 0):
        st.write("Couldn't find experience")
        dicc.update({"Experience":"NOT FOUND"})
        dicc.update({"Career Breaks":"NOT FOUND"})
        dicc.update({"Job Switches":"NOT FOUND"})
    else:
        if(less_than_12 < 2):
            total_score = total_score + 10
            print("total score after job duration - " + str(total_score))
            st.write(f"**Candidate hasn't switched jobs before completing 12 months of tenure**")
            st.write(f":red[Score till now] - **({str(total_score)}/50)**")
            dicc.update({"Job Switches":"PASS"})
        else:
            print("leaving orgs early")
            st.write("**Candidate has switched jobs before completing 12 months of tenure**")
            dicc.update({"Job Switches":"FAIL"})

        if(total_experience/12 < minimum_exp):
            print("Minimum Experience Criteria Doesn't match")
            st.write("***:red[MINIMUM EXPERIENCE CRITERIA DOESN'T MATCH]***")
            # total_score = -100
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
            print("having more than one 3 month career break")
            st.write(f"**Candidate has more than one career break of 3 months each**")
            st.write(f":red[Score till now] - **({str(total_score)}/50)**")
            dicc.update({"Career Breaks":"FAIL"})
   

    st.write(f"Scores found in the resume : {academic_scores}")
    score = extract_scores(academic_scores)
    if(score == 1):
        total_score = total_score+5
        st.write(f"Candidate has academic scores in the acceptable range")
    else:
        st.write(f"Candidate has below par scores or no score found")
    
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
        if(words_in_pdf/total_words >= 0.4):
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
    if(tech_skills_para is None):
        print("andar")
        tech_skills_para = extract_content_between_keywords(text, 'Technical Skills Required', 'Behavioural Skills Required')
    if(tech_skills_para is None):
        tech_skills_para = extract_content_between_keywords(text, 'Skills Required', 'Job Responsibilities')
    
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
    try:
        minimum_exp = int(pattern.search(min_ex[0]).group(1)) if pattern.search(min_ex[0]) else None
    except Exception as e:
        st.write("Couldn't parse minimum experience, please write")
        minimum_exp = int(st.text_input("Please enter a single digit"))
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
                    print(text_content)
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
            try:
                runningmain(text_content, uploaded_resume.name, text)
            except Exception as e:
                try:
                    runningmain(text_content, uploaded_resume.name, text)
                except Exception as e:
                    st.write("exception with this one")
                    st.write(e)


sorted_scores = sorted(list_of_score.items(), key=lambda x: x[1]['TOTAL SCORE'], reverse=True)

data = []
for file_name, attributes in sorted_scores:
    row = [file_name]
    row.extend(attributes.values())
    data.append(row)

df = pd.DataFrame(data, columns=["File Name", "Job Switch", "Experience", "Career Breaks", "Keyword Matching Percentage", "Similarity Score", "Result", "Total Score"])

csv = df.to_csv().encode('utf-8')

st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='large_df.csv',
    mime='text/csv',
)
