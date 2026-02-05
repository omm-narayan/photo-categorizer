import streamlit as st
import cv2
import numpy as np
import os
from PIL import Image
import shutil
from pathlib import Path
import tempfile

st.set_page_config(page_title="Photo Categorizer", layout="wide")

st.title("AI Photo Categorizer")
st.markdown("Organize photos using face detection")

class SimpleFaceCategorizer:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "registered").mkdir(exist_ok=True)
        (self.data_dir / "categorized").mkdir(exist_ok=True)
        
    def detect_faces_opencv(self, image_path):
        """Simple face detection using OpenCV"""
        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                return []
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Load face cascade classifier
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            return faces
            
        except Exception as e:
            st.error(f"Error detecting faces: {e}")
            return []
    
    def register_person(self, name, sample_images):
        """Register a person by saving their sample images"""
        person_dir = self.data_dir / "registered" / name
        person_dir.mkdir(exist_ok=True)
        
        for idx, img_path in enumerate(sample_images):
            dest_path = person_dir / f"sample_{idx+1}.jpg"
            shutil.copy(img_path, dest_path)
        
        return True
    
    def process_photo(self, image_path, person_name):
        """Process and categorize a single photo"""
        faces = self.detect_faces_opencv(image_path)
        
        if len(faces) > 0:
            # Create person's folder
            output_dir = self.data_dir / "categorized" / person_name
            output_dir.mkdir(exist_ok=True)
            
            # Save the photo
            dest_path = output_dir / Path(image_path).name
            shutil.copy(image_path, dest_path)
            
            return {
                'status': 'success',
                'person': person_name,
                'faces_detected': len(faces),
                'destination': str(dest_path)
            }
        else:
            # No faces detected
            unknown_dir = self.data_dir / "categorized" / "unknown"
            unknown_dir.mkdir(exist_ok=True)
            
            dest_path = unknown_dir / Path(image_path).name
            shutil.copy(image_path, dest_path)
            
            return {
                'status': 'no_faces',
                'destination': str(dest_path)
            }

# Initialize categorizer
categorizer = SimpleFaceCategorizer()

# Sidebar
with st.sidebar:
    st.header("👤 Register Person")
    person_name = st.text_input("Enter person name")
    
    uploaded_samples = st.file_uploader(
        "Upload sample photos",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )
    
    if st.button("Register Person") and person_name and uploaded_samples:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_paths = []
            for uploaded_file in uploaded_samples:
                tmp_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(tmp_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                sample_paths.append(tmp_path)
            
            if categorizer.register_person(person_name, sample_paths):
                st.success(f"{person_name} registered!")
    
    st.header("Registered Persons")
    registered_dir = Path("data/registered")
    if registered_dir.exists():
        for person in sorted(registered_dir.iterdir()):
            if person.is_dir():
                st.write(f"• {person.name}")

# Main area
st.header("Upload Photos to Categorize")

uploaded_files = st.file_uploader(
    "Choose photos to organize",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    # Get list of registered persons
    registered_dir = Path("data/registered")
    persons = []
    if registered_dir.exists():
        persons = [p.name for p in registered_dir.iterdir() if p.is_dir()]
    
    if persons:
        selected_person = st.selectbox(
            "Select person to categorize photos under",
            persons + ["Unknown"]
        )
        
        if st.button("Categorize Photos"):
            with st.spinner("Processing..."):
                results = []
                
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        tmp_path = tmp_file.name
                    
                    if selected_person == "Unknown":
                        result = categorizer.process_photo(tmp_path, "unknown")
                    else:
                        result = categorizer.process_photo(tmp_path, selected_person)
                    
                    results.append(result)
                    os.unlink(tmp_path)
                
                # Show results
                st.success(f"Processed {len(results)} photos!")
                
                # Display summary
                categorized = sum(1 for r in results if r['status'] == 'success')
                no_faces = sum(1 for r in results if r['status'] == 'no_faces')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Photos with Faces", categorized)
                with col2:
                    st.metric("No Faces Detected", no_faces)
                
                # Show preview
                with st.expander("View Processed Photos"):
                    for result in results[:5]:  # Show first 5
                        if os.path.exists(result['destination']):
                            img = Image.open(result['destination'])
                            st.image(
                                img,
                                caption=f"Status: {result['status']}",
                                width=200
                            )
    else:
        st.warning("Please register at least one person first!")

# View categorized photos
st.header("View Organized Photos")

categorized_dir = Path("data/categorized")
if categorized_dir.exists() and any(categorized_dir.iterdir()):
    for person_dir in sorted(categorized_dir.iterdir()):
        if person_dir.is_dir():
            photos = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png"))
            if photos:
                with st.expander(f"👤 {person_dir.name} ({len(photos)} photos)"):
                    cols = st.columns(4)
                    for idx, photo in enumerate(photos[:8]):
                        with cols[idx % 4]:
                            img = Image.open(photo)
                            st.image(img, caption=photo.name, use_column_width=True)
else:
    st.info("No categorized photos yet. Upload and categorize some photos!")