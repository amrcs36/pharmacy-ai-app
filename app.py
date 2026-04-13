import streamlit as st
import sqlite3
import json
from datetime import datetime
import base64
from PIL import Image
import io
import re
import pytesseract
# Page configuration
st.set_page_config(
    page_title="AI Pharmacy Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 0rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.1em;
        font-weight: 600;
    }
    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 12px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 12px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 12px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .alert-info {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 12px;
        border-radius: 4px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
def init_db():
    """Initialize SQLite database with drug information."""
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    c = conn.cursor()
    
    # Create drug database
    c.execute('''CREATE TABLE IF NOT EXISTS drugs (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        generic_name TEXT,
        class TEXT,
        indication TEXT,
        side_effects TEXT,
        contraindications TEXT,
        dosage TEXT
    )''')
    
    # Create interaction database
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY,
        drug1 TEXT,
        drug2 TEXT,
        severity TEXT,
        description TEXT
    )''')
    
    # Create audit log
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        timestamp TEXT,
        action TEXT,
        details TEXT
    )''')
    
    # Insert sample drug data
    drugs_data = [
        ("Aspirin", "Acetylsalicylic acid", "NSAID", "Pain, fever, antiplatelet", "GI upset, bleeding", "Bleeding disorders", "500mg-1000mg"),
        ("Metformin", "Metformin", "Antidiabetic", "Type 2 diabetes", "GI upset, lactic acidosis", "Renal impairment", "500mg-2000mg"),
        ("Lisinopril", "Lisinopril", "ACE inhibitor", "Hypertension, heart failure", "Cough, hyperkalemia", "Pregnancy, angioedema", "10mg-40mg"),
        ("Atorvastatin", "Atorvastatin", "Statin", "Hyperlipidemia", "Muscle pain, liver damage", "Liver disease", "10mg-80mg"),
        ("Amoxicillin", "Amoxicillin", "Antibiotic", "Bacterial infection", "Rash, GI upset", "Penicillin allergy", "250mg-500mg"),
        ("Ibuprofen", "Ibuprofen", "NSAID", "Pain, inflammation", "GI upset, kidney issues", "Bleeding disorders", "200mg-400mg"),
        ("Omeprazole", "Omeprazole", "PPI", "GERD, ulcers", "Headache, diarrhea", "None major", "20mg-40mg"),
        ("Metoprolol", "Metoprolol", "Beta-blocker", "Hypertension, angina", "Fatigue, bradycardia", "Asthma, heart block", "25mg-100mg"),
        ("Warfarin", "Warfarin", "Anticoagulant", "Thrombosis prevention", "Bleeding", "Active bleeding", "2mg-10mg"),
        ("Levothyroxine", "Levothyroxine", "Thyroid hormone", "Hypothyroidism", "Palpitations, anxiety", "Hyperthyroidism", "25mcg-200mcg"),
    ]
    
    c.executemany('''INSERT OR IGNORE INTO drugs 
        (name, generic_name, class, indication, side_effects, contraindications, dosage)
        VALUES (?, ?, ?, ?, ?, ?, ?)''', drugs_data)
    
    # Insert interaction data
    interactions_data = [
        ("Aspirin", "Warfarin", "SEVERE", "Increased bleeding risk - avoid combination"),
        ("Aspirin", "Metformin", "MODERATE", "NSAIDs may impair renal function affecting metformin clearance"),
        ("Metformin", "Ibuprofen", "MODERATE", "NSAIDs may reduce metformin efficacy and increase lactic acidosis risk"),
        ("Lisinopril", "Metformin", "MINOR", "ACE inhibitors may increase metformin levels"),
        ("Atorvastatin", "Warfarin", "MODERATE", "Statins may enhance warfarin effect - monitor INR"),
        ("Amoxicillin", "Warfarin", "MODERATE", "Antibiotics may enhance warfarin effect"),
        ("Ibuprofen", "Lisinopril", "MODERATE", "NSAIDs may reduce antihypertensive effect of ACE inhibitors"),
        ("Omeprazole", "Warfarin", "MODERATE", "PPI may enhance warfarin effect"),
        ("Metoprolol", "Lisinopril", "MINOR", "Additive hypotensive effect - monitor BP"),
        ("Levothyroxine", "Omeprazole", "MODERATE", "PPI may reduce levothyroxine absorption"),
    ]
    
    c.executemany('''INSERT OR IGNORE INTO interactions
        (drug1, drug2, severity, description)
        VALUES (?, ?, ?, ?)''', interactions_data)
    
    conn.commit()
    return conn

# Initialize session state
if 'conn' not in st.session_state:
    st.session_state.conn = init_db()
if 'audit_log' not in st.session_state:
    st.session_state.audit_log = []

conn = st.session_state.conn

# Header
st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white; margin-bottom: 20px;">
        <h1>💊 AI Pharmacy Assistant</h1>
        <p style="font-size: 1.1em;">Smart Drug Safety & Prescription Analysis System</p>
    </div>
""", unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Drug Interaction Checker", "📋 Prescription Analyzer", "📊 Drug Database", "📝 Audit Log"])

# ============ TAB 1: Drug Interaction Checker ============
with tab1:
    st.header("Drug-Drug Interaction Checker")
    st.write("Enter medications to check for potential interactions and safety warnings.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Select Medications")
        
        # Get all drugs from database
        c = conn.cursor()
        c.execute("SELECT name FROM drugs ORDER BY name")
        all_drugs = [row[0] for row in c.fetchall()]
        
        num_drugs = st.number_input("Number of medications:", min_value=1, max_value=10, value=2)
        
        selected_drugs = []
        for i in range(num_drugs):
            drug = st.selectbox(f"Medication {i+1}:", all_drugs, key=f"drug_{i}")
            if drug:
                selected_drugs.append(drug)
    
    with col2:
        st.subheader("Patient Information")
        patient_age = st.number_input("Patient Age:", min_value=0, max_value=120, value=50)
        patient_kidney = st.selectbox("Kidney Function:", ["Normal", "Mild impairment", "Moderate impairment", "Severe impairment"])
        patient_liver = st.selectbox("Liver Function:", ["Normal", "Mild impairment", "Moderate impairment", "Severe impairment"])
    
    if st.button("🔍 Check Interactions", key="check_interactions"):
        st.session_state.audit_log.append({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'action': 'Drug Interaction Check',
            'details': f"Checked {len(selected_drugs)} drugs: {', '.join(selected_drugs)}"
        })
        
        st.subheader("Analysis Results")
        
        # Display drug information
        st.write("### Medication Details")
        drug_cols = st.columns(len(selected_drugs))
        
        for idx, drug in enumerate(selected_drugs):
            with drug_cols[idx]:
                c = conn.cursor()
                c.execute("SELECT * FROM drugs WHERE name = ?", (drug,))
                drug_info = c.fetchone()
                
                if drug_info:
                    st.markdown(f"**{drug_info[1]}** ({drug_info[0]})")
                    st.write(f"**Class:** {drug_info[3]}")
                    st.write(f"**Indication:** {drug_info[4]}")
                    st.write(f"**Dosage:** {drug_info[7]}")
                    with st.expander("Side Effects & Warnings"):
                        st.write(f"**Side Effects:** {drug_info[5]}")
                        st.write(f"**Contraindications:** {drug_info[6]}")
        
        # Check interactions
        st.write("### Drug Interactions")
        
        interactions_found = []
        c = conn.cursor()
        
        for i in range(len(selected_drugs)):
            for j in range(i+1, len(selected_drugs)):
                drug1 = selected_drugs[i]
                drug2 = selected_drugs[j]
                
                c.execute("""SELECT * FROM interactions 
                           WHERE (drug1 = ? AND drug2 = ?) OR (drug1 = ? AND drug2 = ?)""",
                         (drug1, drug2, drug2, drug1))
                interaction = c.fetchone()
                
                if interaction:
                    interactions_found.append(interaction)
        
        if interactions_found:
            for interaction in interactions_found:
                severity = interaction[3]
                if severity == "SEVERE":
                    st.markdown(f"""<div class="alert-danger">
                        <strong>⚠️ SEVERE INTERACTION</strong><br>
                        <strong>{interaction[1]} + {interaction[2]}</strong><br>
                        {interaction[4]}
                    </div>""", unsafe_allow_html=True)
                elif severity == "MODERATE":
                    st.markdown(f"""<div class="alert-warning">
                        <strong>⚠️ MODERATE INTERACTION</strong><br>
                        <strong>{interaction[1]} + {interaction[2]}</strong><br>
                        {interaction[4]}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="alert-info">
                        <strong>ℹ️ MINOR INTERACTION</strong><br>
                        <strong>{interaction[1]} + {interaction[2]}</strong><br>
                        {interaction[4]}
                    </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-success">
                <strong>✓ No interactions found</strong><br>
                The selected medications appear to be compatible.
            </div>""", unsafe_allow_html=True)
        
        # Patient-specific warnings
        st.write("### Patient-Specific Considerations")
        
        warnings = []
        if patient_age > 65:
            warnings.append("Elderly patient: Monitor for increased side effects and drug accumulation")
        if patient_kidney != "Normal":
            warnings.append("Renal impairment detected: Many drugs require dose adjustment")
        if patient_liver != "Normal":
            warnings.append("Hepatic impairment detected: Monitor for increased drug levels")
        
        if warnings:
            for warning in warnings:
                st.markdown(f"""<div class="alert-warning">
                    <strong>⚠️ {warning}</strong>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-success">
                <strong>✓ No patient-specific concerns identified</strong>
            </div>""", unsafe_allow_html=True)

# ============ TAB 2: Prescription Analyzer ============
with tab2:
    st.header("OCR Prescription Error Detector")
    st.write("Upload a prescription image or enter prescription details manually for analysis.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Manual Entry")
        
        prescription_text = st.text_area(
            "Enter prescription details:",
            placeholder="e.g., Aspirin 500mg BID x 10 days\nMetformin 500mg TID x 30 days",
            height=150
        )
        
        if st.button("📋 Analyze Prescription", key="analyze_manual"):
            st.session_state.audit_log.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'action': 'Prescription Analysis',
                'details': 'Manual prescription entry analyzed'
            })
            
            st.subheader("Prescription Analysis Results")
            
            # Simple prescription parsing
            lines = prescription_text.strip().split('\n')
            parsed_medications = []
            
            for line in lines:
                # Extract drug name and dosage
                parts = line.split()
                if len(parts) >= 2:
                    drug_name = parts[0]
                    dosage = parts[1] if len(parts) > 1 else "Unknown"
                    frequency = parts[2] if len(parts) > 2 else "Unknown"
                    parsed_medications.append({
                        'name': drug_name,
                        'dosage': dosage,
                        'frequency': frequency
                    })
            
            if parsed_medications:
                st.write("**Extracted Medications:**")
                for med in parsed_medications:
                    st.write(f"- {med['name']} {med['dosage']} {med['frequency']}")
                
                # Check for errors
                st.write("**Safety Checks:**")
                
                errors = []
                c = conn.cursor()
                
                for med in parsed_medications:
                    c.execute("SELECT * FROM drugs WHERE name LIKE ?", (f"%{med['name']}%",))
                    drug = c.fetchone()
                    
                    if not drug:
                        errors.append(f"⚠️ Drug '{med['name']}' not found in database - verify spelling")
                    else:
                        # Check dosage
                        if med['dosage'] and med['dosage'] != "Unknown":
                            st.write(f"✓ {med['name']}: {med['dosage']} (Recommended: {drug[7]})")
                
                # Check drug interactions in prescription
                if len(parsed_medications) > 1:
                    st.write("**Interaction Check:**")
                    for i in range(len(parsed_medications)):
                        for j in range(i+1, len(parsed_medications)):
                            drug1 = parsed_medications[i]['name']
                            drug2 = parsed_medications[j]['name']
                            
                            c.execute("""SELECT * FROM interactions 
                                       WHERE (drug1 LIKE ? AND drug2 LIKE ?) OR (drug1 LIKE ? AND drug2 LIKE ?)""",
                                     (f"%{drug1}%", f"%{drug2}%", f"%{drug2}%", f"%{drug1}%"))
                            interaction = c.fetchone()
                            
                            if interaction:
                                errors.append(f"Interaction: {drug1} + {drug2} ({interaction[3]})")
                
                if errors:
                    for error in errors:
                        st.markdown(f"""<div class="alert-danger">
                            <strong>{error}</strong>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="alert-success">
                        <strong>✓ No errors detected</strong>
                    </div>""", unsafe_allow_html=True)
            else:
                st.warning("No medications could be parsed. Please check the format.")
    
    with col2:
        st.subheader("Image Upload")
        uploaded_file = st.file_uploader("Upload prescription image:", type=['jpg', 'jpeg', 'png', 'gif'])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Prescription", use_column_width=True)
            
            if st.button("🔍 Extract Text from Image", key="extract_ocr"):
                st.session_state.audit_log.append({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'action': 'OCR Prescription Analysis',
                    'details': f'Image: {uploaded_file.name}'
                })
                
try:
                    # قراءة النص من الصورة فعلياً
                    st.info("⏳ جاري تحليل الروشتة واستخراج النص...")
                    extracted_text = pytesseract.image_to_string(image)
                    
                    if extracted_text.strip() == "":
                        st.warning("⚠️ لم يتمكن البرنامج من قراءة النص بوضوح. حاول رفع صورة بإضاءة أفضل.")
                    else:
                        st.success("✅ تم استخراج النص بنجاح!")
                        st.text_area("Extracted Text:", value=extracted_text, height=150)
                        
                except Exception as e:
                    st.error("⚠️ حدث خطأ: محرك Tesseract غير مثبت أو غير متصل.")

# ============ TAB 3: Drug Database ============
with tab3:
    st.header("Drug Database")
    st.write("Browse and search the drug information database.")
    
    search_term = st.text_input("Search drugs:", placeholder="Enter drug name...")
    
    c = conn.cursor()
    
    if search_term:
        c.execute("SELECT * FROM drugs WHERE name LIKE ? OR generic_name LIKE ?", 
                 (f"%{search_term}%", f"%{search_term}%"))
    else:
        c.execute("SELECT * FROM drugs ORDER BY name")
    
    drugs = c.fetchall()
    
    if drugs:
        for drug in drugs:
            with st.expander(f"💊 {drug[1]} ({drug[0]})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Generic Name:** {drug[2]}")
                    st.write(f"**Class:** {drug[3]}")
                    st.write(f"**Indication:** {drug[4]}")
                with col2:
                    st.write(f"**Dosage:** {drug[7]}")
                    st.write(f"**Side Effects:** {drug[5]}")
                    st.write(f"**Contraindications:** {drug[6]}")
    else:
        st.info("No drugs found matching your search.")

# ============ TAB 4: Audit Log ============
with tab4:
    st.header("Audit Log")
    st.write("System activity and usage log for compliance and monitoring.")
    
    if st.session_state.audit_log:
        log_data = []
        for entry in st.session_state.audit_log:
            log_data.append({
                'Timestamp': entry['timestamp'],
                'Action': entry['action'],
                'Details': entry['details']
            })
        
        st.dataframe(log_data, use_container_width=True)
        
        if st.button("📥 Export Audit Log"):
            csv_data = "Timestamp,Action,Details\n"
            for entry in st.session_state.audit_log:
                csv_data += f"{entry['timestamp']},{entry['action']},{entry['details']}\n"
            
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="audit_log.csv",
                mime="text/csv"
            )
    else:
        st.info("No activity logged yet.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.9em; padding: 20px;">
    <p>AI Pharmacy Assistant v1.0 | Community Pharmacy Practice PP 602</p>
    <p>Faculty of Pharmacy - Mansoura National University</p>
    <p>⚠️ For educational purposes only. Not for clinical use without proper validation.</p>
</div>
""", unsafe_allow_html=True)
