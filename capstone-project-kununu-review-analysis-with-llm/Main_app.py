import streamlit as st
import os
import glob
import json
import sys
import time
import io
from datetime import datetime
from contextlib import redirect_stdout

from scripts.word_cloud_generator import get_wordcloud_image
from scripts.tree_map_generator import get_treemap_figure

st.set_page_config(
    page_title="Kununu Reviews Scraper & LLM Analyzer",
    layout="wide",
)

for _ in range(2):
    st.sidebar.write("")

st.sidebar.markdown("""
**by Ngoc My Nguyen**  
Master's Program Data Science – FH Kiel  
Capstone Project – Social Media Analytics
""")

sys.path.append('./scripts')


try:
    from scripts.kununu_scraper import get_all_reviews_for_url, extract_company_name_from_url, generate_filename
    from scripts.llm_analyzer import (
        extract_company_name_from_filename,
        process_individual_prompts,
        combine_json_responses,
        get_current_date
    )
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.error("Make sure kununu_scraper.py and llm_analyzer.py are in the 'scripts' folder")

def scraping_section():
    st.header("🔍 Web Scraping")

    url_input = st.text_input(
        "URL of the company for scraping:",
        placeholder="https://www.kununu.com/de/company-name/kommentare",
        help="Enter the Kununu URL of the company you want to scrape"
    )
    
    max_reviews = st.number_input(
        "Maximum number of reviews to scrape (default is 100 and from the last 2 years):",
        min_value=1,
        max_value=1000,
        value=100,
        help="Maximum number of reviews to collect"
    )
    
    if st.button("Start Scraping", type="primary"):
        if not url_input:
            st.warning("Please enter a valid URL")
            return

        with st.spinner("Scraping reviews... This may take a while. Do not refresh page or switch to the 'Browse reviews' page."):
            try:
                data_dir = "./data"
                os.makedirs(data_dir, exist_ok=True)
                
                company_name = extract_company_name_from_url(url_input)
                filename = generate_filename(company_name)
                save_path = os.path.join(data_dir, filename)
                
                st.info(f"Saving to: {save_path}")
                
                f = io.StringIO()
                with redirect_stdout(f):
                    result = get_all_reviews_for_url(
                        url_input,
                        save_path=save_path,
                        max_reviews=max_reviews
                    )
                
                output = f.getvalue()
                if output:
                    st.text_area("Scraping Messages:", value=output, height=200)
                
                if result:
                    num_reviews = len(list(result.values())[0]) if result else 0
                    st.success(f"Successfully scraped {num_reviews} reviews!")
                    st.success(f"File saved to: {save_path}")
                else:
                    st.error("No reviews were scraped")
                    
            except Exception as e:
                st.error(f"Error during scraping: {str(e)}")
                st.error("Make sure you have Chrome browser installed and the URL is valid")

def file_selection_section():
    data_folder = "./data"
    
    if not os.path.exists(data_folder):
        st.warning("Data folder not found. Please scrape some data first.")
        os.makedirs(data_folder, exist_ok=True)
        return None
    
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    
    if not json_files:
        st.warning("No JSON files found in the data folder")
        return None
    
    file_options = [os.path.basename(f) for f in json_files]
    selected_file = st.selectbox(
        "**Select a file from the data folder:**",
        options=file_options,
        help="Choose a JSON file containing scraped reviews"
    )
    
    if not selected_file:
        return None
        
    selected_file_path = os.path.join(data_folder, selected_file)
    
    if os.path.exists(selected_file_path):
        file_size = os.path.getsize(selected_file_path)
        file_modified = datetime.fromtimestamp(os.path.getmtime(selected_file_path))
        st.info(f"Selected: {selected_file} | Size: {file_size} bytes | Modified: {file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
        
        with st.expander("Preview file content"):
            try:
                with open(selected_file_path, "r", encoding="utf-8") as f:
                    preview_data = json.load(f)
                    if isinstance(preview_data, dict):
                        for url, reviews in preview_data.items():
                            st.write(f"**URL:** {url}")
                            st.write(f"**Number of reviews:** {len(reviews) if isinstance(reviews, list) else 'Unknown'}")
                            if isinstance(reviews, list) and len(reviews) > 0:
                                st.json(reviews[0])
                            break
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    return selected_file_path

def result_file_selection_section():
    results_folder = "./results"
    if not os.path.exists(results_folder):
        st.warning("Results folder not found. Please run the LLM analysis first.")
        os.makedirs(results_folder, exist_ok=True)
        return None
    json_files = glob.glob(os.path.join(results_folder, "*.json"))
    if not json_files:
        st.warning("No JSON files found in the results folder")
        return None
    file_options = [os.path.basename(f) for f in json_files]
    selected_file = st.selectbox(
        "**Select a results file for visualization:**",
        options=file_options,
        help="Choose a JSON file with LLM analysis results"
    )
    if not selected_file:
        return None
    selected_file_path = os.path.join(results_folder, selected_file)
    return selected_file_path


def validate_selected_prompts(selected_prompts):
    if not os.path.exists("./prompts"):
        st.error("Prompts folder not found. Please create './prompts' folder with prompt_1.txt to prompt_13.txt files")
        return False
    
    missing_prompts = []
    for prompt_num in selected_prompts:
        prompt_file = f"./prompts/prompt_{prompt_num}.txt"
        if not os.path.exists(prompt_file):
            missing_prompts.append(f"prompt_{prompt_num}.txt")
    
    if missing_prompts:
        st.error(f"Missing prompt files: {', '.join(missing_prompts)}")
        return False
    
    return True


def llm_analysis_section():
    st.header("🤖 LLM Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        api_key = st.text_input(
            "API Key:",
            type="password",
            help="Enter your Google Generative AI API key"
        )
    
    with col2:
        model_name = st.text_input(
            "Model Name:",
            value="gemini-2.5-flash-preview-05-20",
            help="Enter the model name to use for analysis"
        )
    
    st.write("") 
    st.write("") 
    st.write("**Select Analysis Categories:**")
    
    select_all = st.checkbox("Select All Prompts", value=True)
    
    prompt_descriptions = {
        1: "Arbeitsatmosphäre",
        2: "Image", 
        3: "Work-Life-Balance",
        4: "Karriere/Weiterbildung",
        5: "Gehalt/Sozialleistungen",
        6: "Umwelt-/Sozialbewusstsein",
        7: "Umgang mit älteren Kollegen",
        8: "Vorgesetztenverhalten",
        9: "Arbeitsbedingungen",
        10: "Kommunikation",
        11: "Gleichberechtigung",
        12: "Interessante Aufgaben",
        13: "Sonstiges (alle anderen relevanten Punkte)"
    }
    
    selected_prompts = {}
    
    cols = st.columns(3)
    
    for i, (prompt_num, description) in enumerate(prompt_descriptions.items()):
        col_index = i % 3
        with cols[col_index]:
            default_value = select_all
            selected_prompts[prompt_num] = st.checkbox(
                f"Prompt {prompt_num}: {description}",
                value=default_value,
                key=f"prompt_{prompt_num}"
            )
    
    selected_prompt_numbers = [num for num, selected in selected_prompts.items() if selected]
    
    if selected_prompt_numbers:
        st.info(f"Selected prompts: {', '.join(map(str, selected_prompt_numbers))}")
    else:
        st.warning("Please select at least one prompt to analyze.")
    
    st.write("") 
    st.write("") 
    selected_file_path = file_selection_section()


    if st.button("Start LLM Analysis", type="primary"):
        if not api_key:
            st.error("Please enter your API key")
            return
                
        if not selected_file_path:
            st.error("Please select a file to analyze")
            return
        
        if not selected_prompt_numbers:
            st.error("Please select at least one prompt to analyze")
            return
        
        if not validate_selected_prompts(selected_prompt_numbers):
            return
                

        with st.spinner("Analyzing the reviews... This will take from several minutes to hours depending on the number of reviews and prompts. Do not refresh page or switch to the 'Browse reviews' page."):
            run_llm_analysis(selected_file_path, api_key, selected_prompt_numbers)
        
def run_llm_analysis(selected_file_path, api_key, selected_prompts):
    try:
        with open(selected_file_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)
        
        company_name = extract_company_name_from_filename(selected_file_path)
        current_date = get_current_date()
        
        os.makedirs("./responses", exist_ok=True)
        os.makedirs("./results", exist_ok=True)
        
        total_prompts = len(selected_prompts)
        progress_bar = st.progress(0)
        status_text = st.empty()
        message_placeholder = st.empty()
        all_messages = []
        
        for i, prompt_num in enumerate(selected_prompts):
            status_text.text(f"Processing prompt {prompt_num}... ({i+1}/{total_prompts})")
            progress_bar.progress(i / total_prompts)
            
            f = io.StringIO()
            with redirect_stdout(f):
                result = process_individual_prompts(
                    input_data,
                    prompt_num,
                    company_name,
                    current_date,
                    api_key
                )
            
            prompt_output = f.getvalue()
            if prompt_output:
                all_messages.append(f"=== Prompt {prompt_num} ===\n{prompt_output}")
            
            combined_messages = "\n".join(all_messages)
            message_placeholder.text_area(
                "LLM Analysis Messages:",
                value=combined_messages,
                height=300
            )
            
            progress_bar.progress((i + 1) / total_prompts)
            
            if result is None:
                st.warning(f"Prompt {prompt_num} failed")
            
            if i < len(selected_prompts) - 1:
                time.sleep(30)
        
        status_text.text("Combining responses...")
        f = io.StringIO()
        with redirect_stdout(f):
            combine_json_responses(company_name, current_date, selected_prompts)
        
        combine_output = f.getvalue()
        if combine_output:
            all_messages.append(f"=== Combining Results ===\n{combine_output}")
            combined_messages = "\n".join(all_messages)
            message_placeholder.text_area(
                "LLM Analysis Messages:",
                value=combined_messages,
                height=300
            )
        
        status_text.text("Analysis completed!")
        progress_bar.progress(1.0)
        
        st.success("LLM Analysis completed successfully!")
        st.info("Results saved to the responses and results folders")
        
        results_file = f"./results/result_{company_name}_{current_date}.json"
        if os.path.exists(results_file):
            
            with st.expander("Preview Results"):
                try:
                    with open(results_file, "r", encoding="utf-8") as rf:
                        results_data = json.load(rf)
                        st.json({"Number of categories analyzed": len(results_data.get("categories", []))})
                        if results_data.get("categories"):
                            st.write("**Sample category result:**")
                            st.json(results_data["categories"][0] if results_data["categories"] else {})
                except Exception as e:
                    st.error(f"Error reading results file: {e}")
                    
    except Exception as e:
        st.error(f"Error during LLM analysis: {str(e)}")

def result_visualization_section():
    st.header("📊 Result Visualizations")
    selected_file_path = result_file_selection_section()
    if not selected_file_path:
        return

    if st.button("Start Creating Visualizations", type="primary"):
        with open(selected_file_path, "r", encoding="utf-8") as f:
            results_data = json.load(f)
        categories = results_data.get("categories", [])
        for i, cat_dict in enumerate(categories):
            category = list(cat_dict.keys())[0]
            with st.expander(f"{category.replace('_', ' ').title()}", expanded=(i == 0)):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Wordcloud – Positive Points**")
                    img = get_wordcloud_image(selected_file_path, category, "positive_points")
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.info("No wordcloud available.")
                with col2:
                    st.markdown("**Wordcloud – Critical Points**")
                    img = get_wordcloud_image(selected_file_path, category, "critical_points")
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.info("No wordcloud available.")

                st.write("")
                st.write("")

                col3, col4 = st.columns(2)
                with col3:
                    st.markdown("**Treemap – Positive Points**")
                    fig = get_treemap_figure(selected_file_path, category, "positive_points")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No treemap available.")
                with col4:
                    st.markdown("**Treemap – Critical Points**")
                    fig = get_treemap_figure(selected_file_path, category, "critical_points")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No treemap available.")

def main():
    st.title("Kununu Reviews Scraper & LLM Analyzer")
    st.markdown("Note: English reviews will be translated to German for analysis.")
    st.markdown("---")
    scraping_section()
    st.markdown("---")
    llm_analysis_section()
    st.markdown("---")
    result_visualization_section()

if __name__ == "__main__":
    main()