import streamlit as st
import cv_parser
import tailor_agent
import json
import requests
import os
import hashlib
import io
import PyPDF2
import docx

# 1. 刚性策略配置（符合 AGENTS.md 规范）
MAX_KEYWORDS = 20
FALLBACK_KEYWORDS = ["Project Manager"]
PROVIDER_MODELS = {
    "Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
    "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    "Anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
}

# Callback to add custom keyword safely without violating widget-state rules
def add_keyword_callback():
    if "custom_keyword_input" in st.session_state:
        val = st.session_state.custom_keyword_input.strip()
        if val:
            if "extracted_keywords" not in st.session_state:
                st.session_state.extracted_keywords = []
            if val not in st.session_state.extracted_keywords:
                st.session_state.extracted_keywords.append(val)
            # Clear text input safely
            st.session_state.custom_keyword_input = ""

# Translation resources - Streamlined & shortened for maximum clarity (can be edited manually)
LANG = {
    "English": {
        "title": "Job Application Assistant",
        "caption": "Extract keywords from resumes and tailor cover letters.",
        "credentials_header": "API Configuration",
        "gemini_key": "API Key:",
        "gemini_key_help": "Required for keyword extraction and cover letter generation.",
        "submit_verify": "Verify Connection",
        "conn_success": "Connected successfully",
        "conn_failed": "Connection failed: ",
        "conn_waiting": "Please verify your connection.",
        "demo_mode": "Demo Mode: Search local Swiss jobs database",
        "demo_mode_help": "Retrieves local jobs when API access is restricted.",
        "demo_mode_active": "Demo mode active (searching local Swiss database).",
        "model_selection": "AI Models Selection",
        "cv_parser_model": "CV Parser model:",
        "tailor_agent_model": "Tailor Agent model:",
        "cv_input_header": "Resume Ingestion",
        "cv_uploader_label": "Upload Resume (PDF, DOCX, TXT)",
        "cv_paste_label": "Resume Text:",
        "cv_placeholder": "Paste your resume text here...",
        "analyze_btn": "Extract Resume Keywords",
        "cv_empty_warning": "Please provide your resume first.",
        "cache_hit_keywords": "Loaded cached resume keywords.",
        "parsing_status": "Extracting keywords...",
        "sandbox_connecting": "Ingesting text...",
        "parse_success": "Keywords extracted successfully.",
        "sandbox_success": "Security assertion active.",
        "parse_failed": "Parsing failed: ",
        "fallback_activated": "Using default fallback keywords.",
        "matching_header": "Job Matching",
        "no_keywords": "No keywords found. Using fallback: ['Project Manager'].",
        "human_in_loop": "Select keywords to search:",
        "add_custom_kw": "Add custom keyword:",
        "add_custom_kw_placeholder": "Type keyword and press Enter...",
        "warning_max_kw": "Limit exceeded. Select fewer keywords.",
        "search_btn": "Search Swiss Jobs",
        "searching_spinner": "Searching...",
        "api_fail_fallback": "API error. Using local Swiss database.",
        "local_store_failed": "Save failed: ",
        "no_jobs_found": "No positions found. Try other keywords.",
        "personalization_header": "Tailor Cover Letter",
        "job_select_label": "Select target job:",
        "template_style_label": "Select style:",
        "custom_job_option": "Enter custom job manually...",
        "custom_job_title": "Job Title:",
        "custom_org": "Company:",
        "custom_jd": "Job Description:",
        "custom_jd_placeholder": "Paste job requirements here...",
        "review_jd": "Target Job Details:",
        "req_cv_warning": "Please enter your resume text first.",
        "req_jd_warning": "Please select or write a job description.",
        "cache_hit_cl": "Loaded cached cover letter draft.",
        "tailoring_spinner": "Generating cover letter...",
        "cl_success": "Cover letter generated successfully.",
        "cl_draft_header": "Draft Cover Letter",
        "cl_edit_label": "Edit your draft below:",
        "cv_sug_header": "Resume Suggestions",
        "save_local_btn": "Save as cover_letter.txt",
        "save_success": "Saved to cover_letter.txt successfully.",
        "save_failed": "Save failed: ",
        "export_btn": "Download txt file",
        "search_reminder": "Keywords ready. Search jobs to proceed.",
        "col_title": "Title",
        "col_org": "Company",
        "col_keyword": "Keyword",
        "col_url": "URL",
        "col_apply": "How to Apply",
        "generate_cl_btn": "Generate Cover Letter"
    },
    "Français": {
        "title": "Assistant Candidature",
        "caption": "Extrayez les mots-clés et personnalisez vos lettres de motivation.",
        "credentials_header": "Configuration API",
        "gemini_key": "Clé API :",
        "gemini_key_help": "Requis pour l'analyse et la génération de lettres.",
        "submit_verify": "Vérifier la connexion",
        "conn_success": "Connexion réussie",
        "conn_failed": "Échec de la connexion : ",
        "conn_waiting": "Veuillez vérifier votre connexion.",
        "demo_mode": "Mode Démo : Utiliser la base suisse locale",
        "demo_mode_help": "Récupère les offres locales si les API sont limitées.",
        "demo_mode_active": "Mode démo activé (base suisse locale).",
        "model_selection": "Sélection des Modèles",
        "cv_parser_model": "Modèle CV Parser :",
        "tailor_agent_model": "Modèle Tailor Agent :",
        "cv_input_header": "Saisie du CV",
        "cv_uploader_label": "Télécharger un CV (PDF, DOCX, TXT)",
        "cv_paste_label": "Texte du CV :",
        "cv_placeholder": "Collez votre CV ici...",
        "analyze_btn": "Extraire les mots-clés",
        "cv_empty_warning": "Veuillez d'abord fournir votre CV.",
        "cache_hit_keywords": "Mots-clés chargés depuis le cache.",
        "parsing_status": "Extraction des mots-clés...",
        "sandbox_connecting": "Traitement du texte...",
        "parse_success": "Mots-clés extraits.",
        "sandbox_success": "Sécurité active.",
        "parse_failed": "Échec : ",
        "fallback_activated": "Mots-clés par défaut activés.",
        "matching_header": "Recherche d'Emplois",
        "no_keywords": "Aucun mot-clé. Valeur par défaut : ['Project Manager'].",
        "human_in_loop": "Sélectionnez les mots-clés :",
        "add_custom_kw": "Ajouter un mot-clé :",
        "add_custom_kw_placeholder": "Tapez et appuyez sur Entrée...",
        "warning_max_kw": "Limite dépassée. Sélectionnez moins de mots-clés.",
        "search_btn": "Rechercher des emplois",
        "searching_spinner": "Recherche...",
        "api_fail_fallback": "Erreur API. Utilisation de la base suisse locale.",
        "local_store_failed": "Échec : ",
        "no_jobs_found": "Aucun emploi trouvé. Modifiez vos mots-clés.",
        "personalization_header": "Personnaliser la Lettre",
        "job_select_label": "Sélectionnez l'offre :",
        "template_style_label": "Sélectionnez le style :",
        "custom_job_option": "Saisir une offre manuellement...",
        "custom_job_title": "Titre du poste :",
        "custom_org": "Entreprise :",
        "custom_jd": "Description du poste :",
        "custom_jd_placeholder": "Collez les détails de l'offre ici...",
        "review_jd": "Détails de l'offre cible :",
        "req_cv_warning": "Veuillez d'abord saisir le texte de votre CV.",
        "req_jd_warning": "Veuillez sélectionner ou saisir une description.",
        "cache_hit_cl": "Lettre de motivation chargée du cache.",
        "tailoring_spinner": "Génération de la lettre...",
        "cl_success": "Lettre de motivation générée.",
        "cl_draft_header": "Brouillon de la Lettre",
        "cl_edit_label": "Modifiez votre brouillon ci-dessous :",
        "cv_sug_header": "Suggestions d'optimisation",
        "save_local_btn": "Enregistrer sous cover_letter.txt",
        "save_success": "Enregistré avec succès dans cover_letter.txt.",
        "save_failed": "Échec : ",
        "export_btn": "Télécharger le fichier txt",
        "search_reminder": "Mots-clés prêts. Lancez la recherche.",
        "col_title": "Titre",
        "col_org": "Entreprise",
        "col_keyword": "Mot-clé",
        "col_url": "URL",
        "col_apply": "Postuler",
        "generate_cl_btn": "Générer la lettre"
    }
}

# Set layout centered to align with single-column visual direction
st.set_page_config(
    page_title="AI Job Assistant",
    page_icon="CH",
    layout="centered"
)

# Initialize Session State values
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "cv_hash" not in st.session_state:
    st.session_state.cv_hash = None
if "cv_text" not in st.session_state:
    st.session_state.cv_text = ""
if "extracted_keywords" not in st.session_state:
    st.session_state.extracted_keywords = []
if "retrieved_jobs" not in st.session_state:
    st.session_state.retrieved_jobs = []
if "last_job_sig" not in st.session_state:
    st.session_state.last_job_sig = None
if "tailored_cl" not in st.session_state:
    st.session_state.tailored_cl = ""
if "tailored_sug" not in st.session_state:
    st.session_state.tailored_sug = ""
if "api_connection_status" not in st.session_state:
    st.session_state.api_connection_status = "untested"
if "api_connection_error" not in st.session_state:
    st.session_state.api_connection_error = ""
if "available_models" not in st.session_state:
    st.session_state.available_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "English"
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "Gemini"

# Custom CSS - Force white color on all nested text elements inside stButtons
st.markdown("""
<style>
    /* Import Google Fonts (DM Sans for clean geometric tech headers, Inter for body) */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@700;800;900&family=Inter:wght@400;500;600&display=swap');

    /* Clean Light Background */
    .stApp {
        background-color: #FAFAF9;
    }
    
    /* Global Text Styling (Inter Font) */
    body, p, label, span, li {
        color: #2D2E33 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Sidebar Background color & Font */
    section[data-testid="stSidebar"] {
        background-color: #F3F4F6 !important; /* Neutral light silver-grey sidebar */
        border-right: 1px solid #E5E7EB !important;
    }
    
    section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Card/Container styling - Pink outlines replaced with clean light gray borders */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
        padding: 24px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 20px !important;
    }
    
    /* Modern DM Sans Headers in soft dark grey */
    h1, h2, h3, h4, h5, h6 {
        color: #2D2E33 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Dark grey buttons with white text, no pink outlines */
    div.stButton > button, div.stButton > button p, div.stButton > button span, div.stButton > button div {
        background-color: #374151 !important; /* Dark Grey */
        color: #FFFFFF !important; /* White Text */
        border: none !important; /* No outlines */
        border-radius: 6px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    }
    div.stButton > button:hover, div.stButton > button:hover p, div.stButton > button:hover span {
        background-color: #1F2937 !important; /* Darker Grey on hover */
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Primary buttons override - Same styling */
    div.stButton > button[type="primary"], div.stButton > button[type="primary"] p, div.stButton > button[type="primary"] span {
        background-color: #111827 !important; /* Deep Charcoal Black */
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }
    div.stButton > button[type="primary"]:hover, div.stButton > button[type="primary"]:hover p, div.stButton > button[type="primary"]:hover span {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Neutralized alerts */
    .stAlert {
        border-radius: 6px !important;
        border: 1px solid #E5E7EB !important;
        background-color: #F9FAFB !important;
        color: #2D2E33 !important;
    }
    
    /* Input border formatting */
    input, textarea, select {
        border-color: #E5E7EB !important;
    }
    input:focus, textarea:focus {
        border-color: #4B5563 !important;
        box-shadow: 0 0 0 2px rgba(75, 85, 99, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# Define language and page title
selected_lang = st.session_state.selected_lang

# Sidebar Layout (Emoji-free)
st.sidebar.markdown("<h2 style='text-align: center; color: #2D2E33; margin-top: 10px;'>Job Assistant</h2>", unsafe_allow_html=True)

selected_lang = st.sidebar.selectbox(
    "Language / Langue",
    options=["English", "Français"],
    index=0 if st.session_state.selected_lang == "English" else 1
)
st.session_state.selected_lang = selected_lang

st.sidebar.write("---")
st.sidebar.markdown("<h4 style='color: #5A6275;'>Flow Steps</h4>", unsafe_allow_html=True)

# Multilingual labels for sidebar steps (Emoji-free)
step1_lbl = "1. Configuration"
step2_lbl = "2. CV Ingestion" if selected_lang == "English" else "2. Saisie du CV"
step3_lbl = "3. Job Matching" if selected_lang == "English" else "3. Recherche d'Emploi"
step4_lbl = "4. Tailoring" if selected_lang == "English" else "4. Personnalisation"

# Highlight active step using Y2K monospace notation
lbl_s1 = f"[Active] {step1_lbl}" if st.session_state.current_step == 1 else step1_lbl
lbl_s2 = f"[Active] {step2_lbl}" if st.session_state.current_step == 2 else step2_lbl
lbl_s3 = f"[Active] {step3_lbl}" if st.session_state.current_step == 3 else step3_lbl
lbl_s4 = f"[Active] {step4_lbl}" if st.session_state.current_step == 4 else step4_lbl

# Navigation buttons with locks
if st.sidebar.button(lbl_s1, use_container_width=True):
    st.session_state.current_step = 1
    st.rerun()

if st.sidebar.button(lbl_s2, use_container_width=True):
    st.session_state.current_step = 2
    st.rerun()

s3_disabled = not st.session_state.extracted_keywords
if st.sidebar.button(lbl_s3, use_container_width=True, disabled=s3_disabled, help="Extract keywords in Step 2 to unlock"):
    st.session_state.current_step = 3
    st.rerun()

s4_disabled = not st.session_state.retrieved_jobs
if st.sidebar.button(lbl_s4, use_container_width=True, disabled=s4_disabled, help="Ingest job records in Step 3 to unlock"):
    st.session_state.current_step = 4
    st.rerun()

# ----------------- MAIN TITLE (DM Sans Header) -----------------
st.write(f"## {LANG[selected_lang]['title']}")
st.caption(LANG[selected_lang]["caption"])
st.write("---")

# ----------------- STEP 1: API CONFIGURATION -----------------
if st.session_state.current_step == 1:
    with st.container(border=True):
        st.subheader(LANG[selected_lang]["credentials_header"])
        
        # Load LLM Provider choice
        selected_provider = st.selectbox(
            "LLM Provider:",
            options=["Gemini", "OpenAI", "Anthropic"],
            index=["Gemini", "OpenAI", "Anthropic"].index(st.session_state.llm_provider)
        )
        st.session_state.llm_provider = selected_provider
        os.environ["LLM_PROVIDER"] = selected_provider
        
        # Load default keys
        env_api_key = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        if env_api_key == "YOUR_MOCK_KEY":
            env_api_key = ""
            
        api_key_input = st.text_input(
            LANG[selected_lang]["gemini_key"],
            value=st.session_state.get("llm_api_key", env_api_key),
            type="password",
            help=LANG[selected_lang]["gemini_key_help"]
        )
        
        if api_key_input:
            st.session_state.llm_api_key = api_key_input
            os.environ["LLM_API_KEY"] = api_key_input
            os.environ["GEMINI_API_KEY"] = api_key_input
        else:
            os.environ["LLM_API_KEY"] = "YOUR_MOCK_KEY"
            os.environ["GEMINI_API_KEY"] = "YOUR_MOCK_KEY"
            
        if st.button(LANG[selected_lang]["submit_verify"], use_container_width=True):
            if not api_key_input:
                st.session_state.api_connection_status = "failed"
                st.session_state.api_connection_error = "API Key is empty!"
            else:
                with st.spinner("Verifying connection..."):
                    try:
                        import llm_router
                        test_models = PROVIDER_MODELS[selected_provider]
                        test_model = test_models[0]
                        
                        llm_router.call_llm(
                            provider=selected_provider,
                            api_key=api_key_input,
                            model_name=test_model,
                            system_instruction="You are a connection verifier. Respond only with 'OK'.",
                            prompt="Ping",
                            response_format_json=False
                        )
                        
                        st.session_state.api_connection_status = "success"
                        st.session_state.api_connection_error = ""
                        st.session_state.llm_api_key = api_key_input
                        os.environ["LLM_API_KEY"] = api_key_input
                        os.environ["GEMINI_API_KEY"] = api_key_input
                        st.session_state.cv_hash = None
                    except Exception as test_err:
                        clean_err = cv_parser.scrub_secrets(str(test_err), api_key_input)
                        st.session_state.api_connection_status = "failed"
                        st.session_state.api_connection_error = clean_err
                        
        if st.session_state.api_connection_status == "success":
            st.success(LANG[selected_lang]["conn_success"])
        elif st.session_state.api_connection_status == "failed":
            st.error(f"{LANG[selected_lang]['conn_failed']}{st.session_state.api_connection_error}")
        else:
            st.info(LANG[selected_lang]["conn_waiting"])
            
        st.write("---")
        st.subheader(LANG[selected_lang]["model_selection"])
        
        provider_models = PROVIDER_MODELS[selected_provider]
        
        # Load safe default model selections based on provider
        try:
            cv_idx = provider_models.index(st.session_state.get("cv_model", ""))
        except ValueError:
            cv_idx = 0
            
        try:
            tailor_idx = provider_models.index(st.session_state.get("tailor_model", ""))
        except ValueError:
            tailor_idx = min(1, len(provider_models)-1)
            
        cv_model_val = st.selectbox(LANG[selected_lang]["cv_parser_model"], provider_models, index=cv_idx)
        tailor_model_val = st.selectbox(LANG[selected_lang]["tailor_agent_model"], provider_models, index=tailor_idx)
        
        st.session_state.cv_model = cv_model_val
        st.session_state.tailor_model = tailor_model_val
        
        # Demo Mode
        st.write("---")
        demo_mode = st.checkbox(
            LANG[selected_lang]["demo_mode"],
            value=st.session_state.get("demo_mode", True),
            help=LANG[selected_lang]["demo_mode_help"]
        )
        st.session_state.demo_mode = demo_mode

# ----------------- STEP 2: CV PARSING & KEYWORDS -----------------
elif st.session_state.current_step == 2:
    with st.container(border=True):
        st.subheader(LANG[selected_lang]["cv_input_header"])
        
        cv_file = st.file_uploader(LANG[selected_lang]["cv_uploader_label"], type=["pdf", "docx", "txt"])
        extracted_text = ""
        
        if cv_file is not None:
            try:
                if cv_file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(cv_file)
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
                elif cv_file.name.endswith('.docx'):
                    doc = docx.Document(cv_file)
                    for para in doc.paragraphs:
                        extracted_text += para.text + "\n"
                elif cv_file.name.endswith('.txt'):
                    extracted_text = cv_file.read().decode('utf-8')
            except Exception as e:
                st.error(f"Read error: {str(e)}")
                
        cv_text = st.text_area(
            LANG[selected_lang]["cv_paste_label"],
            value=extracted_text if extracted_text else st.session_state.get("cv_text", ""),
            height=300,
            placeholder=LANG[selected_lang]["cv_placeholder"]
        )
        st.session_state.cv_text = cv_text
        
        # Extraction button
        if st.button(LANG[selected_lang]["analyze_btn"], use_container_width=True, type="primary"):
            if not cv_text.strip():
                st.warning(LANG[selected_lang]["cv_empty_warning"])
            else:
                provider_models = PROVIDER_MODELS[st.session_state.llm_provider]
                cv_model_selection = st.session_state.get("cv_model", provider_models[0])
                key_for_hash = f"{cv_text.strip()}-{os.getenv('LLM_API_KEY', '')}-{cv_model_selection}"
                current_hash = hashlib.md5(key_for_hash.encode('utf-8')).hexdigest()
                
                if st.session_state.cv_hash == current_hash and st.session_state.extracted_keywords:
                    st.info(LANG[selected_lang]["cache_hit_keywords"])
                else:
                    with st.status(LANG[selected_lang]["parsing_status"], expanded=True) as status:
                        st.write(LANG[selected_lang]["sandbox_connecting"])
                        try:
                            keywords = cv_parser.extract_keywords(cv_text, model_name=cv_model_selection)
                            st.session_state.extracted_keywords = keywords
                            st.session_state.cv_hash = current_hash
                            status.update(label=LANG[selected_lang]["parse_success"], state="complete")
                            st.success(LANG[selected_lang]["sandbox_success"])
                        except Exception as e:
                            st.error(f"{LANG[selected_lang]['parse_failed']}{str(e)}")
                            st.session_state.extracted_keywords = FALLBACK_KEYWORDS
                            st.session_state.cv_hash = current_hash
                            status.update(label=LANG[selected_lang]["fallback_activated"], state="error")
                            
        st.write("---")
        st.subheader(LANG[selected_lang]["matching_header"])
        
        if not st.session_state.extracted_keywords:
            st.info(LANG[selected_lang]["no_keywords"])
            final_keywords = FALLBACK_KEYWORDS
        else:
            final_keywords = st.multiselect(
                LANG[selected_lang]["human_in_loop"],
                options=st.session_state.extracted_keywords,
                default=st.session_state.extracted_keywords
            )
            
        st.text_input(
            LANG[selected_lang]["add_custom_kw"],
            placeholder=LANG[selected_lang]["add_custom_kw_placeholder"],
            key="custom_keyword_input",
            on_change=add_keyword_callback
        )
        
        # Hard limits check
        if len(final_keywords) > MAX_KEYWORDS:
            st.error(LANG[selected_lang]["warning_max_kw"].format(count=len(final_keywords), max=MAX_KEYWORDS))
            
        st.session_state.final_keywords = final_keywords

# ----------------- STEP 3: JOB MATCHING & INGESTION -----------------
elif st.session_state.current_step == 3:
    with st.container(border=True):
        st.subheader(LANG[selected_lang]["matching_header"])
        
        final_keywords = st.session_state.get("final_keywords", FALLBACK_KEYWORDS)
        demo_mode = st.session_state.get("demo_mode", True)
        
        if st.button(LANG[selected_lang]["search_btn"], type="primary", use_container_width=True):
            with st.spinner(LANG[selected_lang]["searching_spinner"]):
                aggregated_results = []
                
                # Mock Swiss job bank
                local_job_bank = [
                    {
                        "职位名称": "Digital Campaign Specialist",
                        "发布机构/组织": "Richemont",
                        "触发检索关键词": "Marketing",
                        "直达链接/数据源": "https://careers.richemont.com/en/jobs/digital-campaign-specialist-geneva",
                        "申请方式": "请在 Richemont 官方招聘网站提交在线申请：https://careers.richemont.com/"
                    },
                    {
                        "职位名称": "Media Project Manager",
                        "发布机构/组织": "L'Oréal",
                        "触发检索关键词": "Project Manager",
                        "直达链接/数据源": "https://careers.loreal.com/en_US/jobs/JobDetail/Media-Project-Manager-Geneva",
                        "申请方式": "请在 L'Oréal 招聘门户网站提交简历：https://careers.loreal.com/"
                    },
                    {
                        "职位名称": "AI Workflow & Automation Marketing Lead",
                        "发布机构/组织": "Swiss Cyber Institute",
                        "触发检索关键词": "AI / Automation",
                        "直达链接/数据源": "https://swisscyberinstitute.com/jobs/ai-marketing-lead",
                        "申请方式": "请发送您的个人简历及自荐信至邮箱：careers@swisscyberinstitute.com"
                    },
                    {
                        "职位名称": "Digital Marketing & Communications Manager",
                        "发布机构/组织": "WHO (World Health Organization)",
                        "触发检索关键词": "Communication",
                        "直达链接/数据源": "https://careers.who.int/careersection/ex/jobdetail.ftl?job=240321",
                        "申请方式": "请在 WHO 官方招聘门户（WHO Careers Section）提交在线申请"
                    },
                    {
                        "职位名称": "Senior Project Manager - Digital Analytics",
                        "发布机构/组织": "Nestlé",
                        "触发检索关键词": "Project Manager",
                        "直达链接/数据源": "https://www.nestle.com/jobs/vevey-digital-project-manager",
                        "申请方式": "请通过 Nestlé 官方全球招聘系统投递简历：https://www.nestle.com/jobs"
                    },
                    {
                        "职位名称": "E-Commerce Growth Manager",
                        "发布机构/组织": "Nestlé",
                        "触发检索关键词": "Growth",
                        "直达链接/数据源": "https://www.nestle.com/jobs/e-commerce-growth-manager",
                        "申请方式": "请通过 Nestlé 官方全球招聘系统投递简历：https://www.nestle.com/jobs"
                    }
                ]
                
                if demo_mode:
                    st.info(LANG[selected_lang]["demo_mode_active"])
                    for kw in final_keywords:
                        kw_lower = kw.lower()
                        for job in local_job_bank:
                            match_title = kw_lower in job["职位名称"].lower()
                            match_org = kw_lower in job["发布机构/组织"].lower()
                            match_trigger = kw_lower in job["触发检索关键词"].lower()
                            if match_title or match_trigger or match_org:
                                matched_job = job.copy()
                                matched_job["触发检索关键词"] = kw
                                aggregated_results.append(matched_job)
                else:
                    for kw in final_keywords:
                        # ReliefWeb API
                        try:
                            url = "https://api.reliefweb.int/v2/jobs"
                            params = {
                                "appname": "reliefweb-jobsearch",
                                "query[value]": kw,
                                "filter[field]": "country",
                                "filter[value]": "Switzerland",
                                "limit": 3,
                                "profile": "full"
                            }
                            response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                            if response.status_code == 200:
                                api_data = response.json()
                                for item in api_data.get("data", []):
                                    fields = item.get("fields", {})
                                    how_to_apply = fields.get("how_to_apply", "请点击直达链接查看申请方式")
                                    how_to_apply_clean = how_to_apply.replace("<p>", "").replace("</p>", "").replace("<br>", "\n").replace("</a>", "").replace("<ul>", "").replace("<li>", "").replace("</li>", "").replace("</ul>", "")
                                    
                                    aggregated_results.append({
                                        "职位名称": item.get("title", fields.get("title", "未命名岗位")),
                                        "发布机构/组织": fields.get("source", [{}])[0].get("name", "UN/NGO Partner") if fields.get("source") else "International Org",
                                        "触发检索关键词": kw,
                                        "直达链接/数据源": fields.get("url", item.get("url", "https://reliefweb.int")),
                                        "申请方式": how_to_apply_clean[:200] + "..." if len(how_to_apply_clean) > 200 else how_to_apply_clean
                                    })
                        except Exception as e:
                            st.caption(f"ReliefWeb API exception on keyword '{kw}': ({str(e)})")
                            
                        # Swiss Job-Room API
                        try:
                            jr_url = "https://www.job-room.ch/api/jobAdvertisements"
                            jr_params = {"keyword": kw}
                            jr_response = requests.get(jr_url, params=jr_params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                            if jr_response.status_code == 200:
                                jr_data = jr_response.json()
                                content = jr_data.get("content", []) if isinstance(jr_data, dict) else (jr_data if isinstance(jr_data, list) else [])
                                for item in content[:3]:
                                    aggregated_results.append({
                                        "职位名称": item.get("title", "Job-Room Posting"),
                                        "发布机构/组织": item.get("company", {}).get("name", "Swiss Company"),
                                        "触发检索关键词": kw,
                                        "直达链接/数据源": item.get("url", f"https://www.job-room.ch/job-search/{item.get('id', '')}"),
                                        "申请方式": "通过 Job-Room 或 enterprise directly"
                                    })
                        except Exception as e:
                            st.caption(f"Job-Room API exception on keyword '{kw}': ({str(e)})")
                            
                # Fallback to local Swiss bank if API got nothing
                if not aggregated_results:
                    st.caption(LANG[selected_lang]["api_fail_fallback"])
                    for kw in final_keywords:
                        kw_lower = kw.lower()
                        for job in local_job_bank:
                            match_title = kw_lower in job["职位名称"].lower()
                            match_org = kw_lower in job["发布机构/组织"].lower()
                            match_trigger = kw_lower in job["触发检索关键词"].lower()
                            if match_title or match_trigger or match_org:
                                matched_job = job.copy()
                                matched_job["触发检索关键词"] = kw
                                aggregated_results.append(matched_job)
                                
                # Deduplication and local storage
                if aggregated_results:
                    seen_jobs = set()
                    deduped_results = []
                    for job in aggregated_results:
                        job_signature = f"{job['职位名称']}-{job['发布机构/组织']}"
                        if job_signature not in seen_jobs:
                            seen_jobs.add(job_signature)
                            deduped_results.append(job)
                            
                    st.session_state.retrieved_jobs = deduped_results
                    try:
                        with open("easy_jobs_pool.json", "w", encoding="utf-8") as f:
                            json.dump(deduped_results, f, ensure_ascii=False, indent=4)
                    except Exception as store_err:
                        st.error(f"{LANG[selected_lang]['local_store_failed']}{str(store_err)}")
                else:
                    st.warning(LANG[selected_lang]["no_jobs_found"])
                    
        # Render Job Pool & Target Selection
        if st.session_state.retrieved_jobs:
            st.write("---")
            translated_jobs = []
            for job in st.session_state.retrieved_jobs:
                translated_jobs.append({
                    LANG[selected_lang]["col_title"]: job["职位名称"],
                    LANG[selected_lang]["col_org"]: job["发布机构/组织"],
                    LANG[selected_lang]["col_keyword"]: job["触发检索关键词"],
                    LANG[selected_lang]["col_url"]: job["直达链接/数据源"],
                    LANG[selected_lang]["col_apply"]: job["申请方式"]
                })
            st.dataframe(translated_jobs, use_container_width=True)
            
            job_options = [f"{j['职位名称']} @ {j['发布机构/组织']}" for j in st.session_state.retrieved_jobs]
            job_options.append(LANG[selected_lang]["custom_job_option"])
            
            selected_option = st.selectbox(
                LANG[selected_lang]["job_select_label"],
                options=job_options
            )
            
            selected_title = ""
            selected_org = ""
            selected_jd = ""
            
            if selected_option == LANG[selected_lang]["custom_job_option"]:
                selected_title = st.text_input(LANG[selected_lang]["custom_job_title"], value="Media Project Manager")
                selected_org = st.text_input(LANG[selected_lang]["custom_org"], value="Geneva Global Org")
                selected_jd = st.text_area(
                    LANG[selected_lang]["custom_jd"],
                    placeholder=LANG[selected_lang]["custom_jd_placeholder"],
                    height=150
                )
            else:
                idx = job_options.index(selected_option)
                job_data = st.session_state.retrieved_jobs[idx]
                selected_title = job_data["职位名称"]
                selected_org = job_data["发布机构/组织"]
                
                default_jd = (
                    f"Role: {selected_title}\n"
                    f"Organization: {selected_org}\n"
                    f"Key Requirements: Lead digital marketing campaigns, oversee multi-market project execution, "
                    f"collaborate with cross-functional stakeholders, and coordinate programmatic ad layouts.\n"
                    f"Application Info: {job_data.get('申请方式', '')}"
                )
                selected_jd = st.text_area(
                    LANG[selected_lang]["review_jd"],
                    value=default_jd,
                    height=150
                )
                
            st.session_state.selected_title = selected_title
            st.session_state.selected_org = selected_org
            st.session_state.selected_jd = selected_jd

# ----------------- STEP 4: COVER LETTER & CV SUGGESTIONS -----------------
elif st.session_state.current_step == 4:
    with st.container(border=True):
        st.subheader(LANG[selected_lang]["personalization_header"])
        
        template_style = st.selectbox(
            LANG[selected_lang]["template_style_label"],
            options=["Standard Professional", "Aggressive / Direct", "Creative / Marketing"]
        )
        
        selected_title = st.session_state.get("selected_title", "Media Project Manager")
        selected_org = st.session_state.get("selected_org", "Geneva Global Org")
        selected_jd = st.session_state.get("selected_jd", "")
        cv_text = st.session_state.get("cv_text", "")
        
        jd_hash = hashlib.md5(selected_jd.strip().encode('utf-8')).hexdigest()
        cv_hash_val = st.session_state.cv_hash if st.session_state.cv_hash else ""
        current_job_sig = f"{cv_hash_val}-{selected_title}-{jd_hash}-{template_style}"
        
        provider_models = PROVIDER_MODELS[st.session_state.llm_provider]
        tailor_model = st.session_state.get("tailor_model", provider_models[0])
        
        if st.button(LANG[selected_lang]["generate_cl_btn"], type="primary", use_container_width=True):
            if not cv_text.strip():
                cv_text = "Media Project Manager with multi-market campaign programmatic ad experience."
                
            if not selected_jd.strip():
                st.warning(LANG[selected_lang]["req_jd_warning"])
            else:
                if st.session_state.last_job_sig == current_job_sig and st.session_state.tailored_cl:
                    st.info(LANG[selected_lang]["cache_hit_cl"])
                else:
                    with st.spinner(LANG[selected_lang]["tailoring_spinner"] + f"[{template_style}]..."):
                        result = tailor_agent.generate_tailored_materials(
                            cv_text, selected_jd, template_style,
                            model_name=tailor_model, language=selected_lang
                        )
                        st.session_state.tailored_cl = result["cover_letter"]
                        st.session_state.tailored_sug = result["suggestions"]
                        st.session_state.last_job_sig = current_job_sig
                    st.success(LANG[selected_lang]["cl_success"])
                    
        # Output Editor & Preview
        if st.session_state.tailored_cl:
            st.write("---")
            st.subheader(LANG[selected_lang]["cl_draft_header"])
            edited_cl = st.text_area(
                LANG[selected_lang]["cl_edit_label"],
                value=st.session_state.tailored_cl,
                height=350
            )
            
            st.subheader(LANG[selected_lang]["cv_sug_header"])
            st.info(st.session_state.tailored_sug)
            
            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                if st.button(LANG[selected_lang]["save_local_btn"], use_container_width=True):
                    try:
                        with open("cover_letter.txt", "w", encoding="utf-8") as f:
                            f.write(edited_cl)
                        st.success(LANG[selected_lang]["save_success"])
                    except Exception as save_err:
                        st.error(f"{LANG[selected_lang]['save_failed']}{str(save_err)}")
            with col_s2:
                st.download_button(
                    label=LANG[selected_lang]["export_btn"],
                    data=edited_cl,
                    file_name="cover_letter.txt",
                    mime="text/plain",
                    use_container_width=True
                )

# ----------------- FOOTER STEPPER NAVIGATION -----------------
st.write("---")
col_prev, col_spacer, col_next = st.columns([1.5, 2, 1.5])

with col_prev:
    if st.session_state.current_step > 1:
        if st.button("Previous / Retour"):
            st.session_state.current_step -= 1
            st.rerun()

with col_next:
    if st.session_state.current_step < 4:
        can_proceed = True
        lock_message = ""
        
        # Step Lock validations
        if st.session_state.current_step == 2:
            if not st.session_state.extracted_keywords:
                can_proceed = False
                lock_message = "Please extract keywords from your CV before proceeding."
        elif st.session_state.current_step == 3:
            if not st.session_state.retrieved_jobs:
                can_proceed = False
                lock_message = "Please search and select a matched job advertisement."
                
        if can_proceed:
            if st.button("Next / Suivant"):
                st.session_state.current_step += 1
                st.rerun()
        else:
            st.button("Next / Suivant", disabled=True, help=lock_message)
