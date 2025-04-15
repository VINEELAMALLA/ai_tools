import streamlit as st
import nbformat
from nbconvert import PythonExporter
import io
import re
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Set page config for better UI
st.set_page_config(page_title="AI-Powered Tools", layout="wide")

# Custom CSS for improved UI
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
        padding: 20px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stFileUploader {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ddd;
    }
    .option-box {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px;
    }
</style>
""", unsafe_allow_html=True)

def review_notebook(notebook_file):
    try:
        # Read notebook
        notebook_content = notebook_file.read()
        nb = nbformat.reads(notebook_content, as_version=4)
        
        # Convert to python code
        exporter = PythonExporter()
        code, _ = exporter.from_notebook_node(nb)
        
        suggestions = []
        
        # Basic code review rules
        if 'print ' in code:
            suggestions.append("Consider updating print statements to Python 3 format: print()")
        
        if 'except:' in code:
            suggestions.append("Consider specifying exception types in except clauses")
            
        if '# TODO' in code:
            suggestions.append("Found TODO comments - consider addressing these tasks")
            
        # Check for long functions
        functions = re.findall(r'def .*\(.*\):', code)
        for func in functions:
            if len(func) > 50:
                suggestions.append(f"Long function definition found: {func[:30]}... Consider breaking into smaller functions")
        
        return suggestions if suggestions else ["Code looks good! No major suggestions."]
    except Exception as e:
        return [f"Error reviewing notebook: {str(e)}"]

def generate_questions(text):
    sentences = re.split(r'[.!?]+', text)
    questions = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Simple question generation rules
        if sentence.startswith(('He ', 'She ', 'It ', 'They ', 'We ', 'I ')):
            questions.append(f"What did {sentence.split()[0].lower()} do?")
        elif any(word in sentence.lower() for word in ['is', 'are', 'was', 'were']):
            questions.append(f"Why {sentence.lower().split(' is ')[0]}?")
        else:
            questions.append(f"What is the context of '{sentence[:30]}...'?")

    return questions[:20] if questions else ["No questions could be generated from the text."]

def get_leetcode_stats(username):
    try:
        url = "https://leetcode.com/graphql"
        headers = {
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/{username}/"
        }

        query = """
        query getUserProfile($username: String!) {
          matchedUser(username: $username) {
            submitStatsGlobal {
              acSubmissionNum {
                difficulty
                count
              }
            }
            profile {
              ranking
            }
          }
        }
        """

        payload = {
            "operationName": "getUserProfile",
            "variables": {"username": username},
            "query": query
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            try:
                user_data = data["data"]["matchedUser"]
                submissions = user_data["submitStatsGlobal"]["acSubmissionNum"]
                ranking = user_data["profile"]["ranking"]
                stats = {entry["difficulty"]: entry["count"] for entry in submissions if entry["difficulty"] != "All"}
                total = sum(stats.values())
                return stats, total, ranking
            except:
                return None, None, None
        else:
            return None, None, None
    except Exception as e:
        return None, None, None

def main():
    st.title("📊 AI-Powered Tools")
    st.markdown("Select an option below to get started!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("### 📓 Notebook Reviewer")
            notebook_file = st.file_uploader("Upload your notebook (.ipynb)", type=['ipynb'], key="notebook")
            if notebook_file:
                with st.spinner("Reviewing notebook..."):
                    suggestions = review_notebook(notebook_file)
                    st.subheader("Review Suggestions")
                    for suggestion in suggestions:
                        st.markdown(f"- {suggestion}")
            
            st.markdown("### ❓ Question Generator")
            text_input = st.text_area("Enter text to generate questions", height=150)
            num_questions = st.slider("Select number of questions (max 20)", min_value=1, max_value=20, value=5)
            if st.button("Generate Questions"):
                if text_input:
                    with st.spinner("Generating questions..."):
                        questions = generate_questions(text_input)
                        st.subheader("Generated Questions")
                        for q in questions[:num_questions]:
                            st.markdown(f"- {q}")
    
    with col2:
        with st.container():
            st.markdown("### 📈 Profile Analyzer")
            profile_type = st.selectbox("Select platform", ["LeetCode"])
            profile_id = st.text_input(f"Enter {profile_type} ID")
            if st.button("Analyze Profile"):
                if not profile_id:
                    st.error("Please enter a valid ID.")
                elif not re.match(r'^[\w-]+$', profile_id.strip()):
                    st.error("Invalid ID. Use alphanumeric characters and hyphens only.")
                else:
                    with st.spinner(f"Fetching {profile_type} stats for {profile_id}..."):
                        if profile_type == "LeetCode":
                            stats, total, rank = get_leetcode_stats(profile_id.strip())
                            if stats:
                                st.success(f"✅ Stats found for **{profile_id}**")
                                
                                # Metrics
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric(label="✅ Total Solved", value=total)
                                with col2:
                                    st.metric(label="🏆 Global Rank", value=f"#{rank:,}" if rank else "N/A")

                                # Pie chart
                                fig = px.pie(
                                    names=list(stats.keys()),
                                    values=list(stats.values()),
                                    title="Problems by Difficulty",
                                    color_discrete_sequence=px.colors.sequential.RdBu
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                # Raw Stats
                                st.markdown("### 📋 Breakdown")
                                for diff, count in stats.items():
                                    st.write(f"**{diff}:** {count}")
                            else:
                                st.error("❌ Could not retrieve data. Please check the username.")

if __name__ == "__main__":
    main()
