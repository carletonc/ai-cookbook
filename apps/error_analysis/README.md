# DISCLAIMER!
### This work is not my own. The below README.md and files attached are originally from Shaw Talebi. I stumbled upon his youtube channel and found this streamlit app to be so useful that I had to add it to my own repo so I could easily reference it, and modify it for my own use cases. The current state of this repo rearranges Shaw's original code for cleaner organization, but will be modified further to ingest a CSV and export an annotated JSON or CSV. Further, inputs, outputs, and annotations labels will be analyzed by a LLM to come up with labels to analyze error types for iterations. I intend this app to be applicable to any error analysis -- ML or LLMs.

# How to Improve AI Apps with Error Analysis
Example code for LLM error analysis of LinkedIn Ghostwriter.

**Links:**
- [Video link](https://youtu.be/982V2ituTdc)
- [Blog link](https://shawhin.medium.com/how-to-improve-ai-apps-with-error-analysis-4af5f163a1d1)

## Main Python Files
- `1-generate_posts.py` - Main script for generating LinkedIn posts from user inputs using OpenAI API
- `annotation_app.py` - Streamlit application for reviewing and annotating generated posts with binary labels and notes

### Configuration Files
- `requirements.txt` - Python package dependencies (includes JupyterLab, OpenAI, Streamlit, pandas, etc.)
- `.env` - Environment variables configuration (with OPENAI_API_KEY) - *not included in repo*

### Important Directories
- `data/` - Contains input data and generated outputs
  - `inputs.csv` - User input data for post generation
  - `*-request_response.csv` - Generated request-response pairs (timestamped)
  - `*-annotations.csv` - Annotation files created by the annotation app
  - `*-labels.txt` - Binary label configurations for annotation
- `prompts/` - LLM prompt templates
  - `prompt.md` - Main prompt template for LinkedIn post generation

Note: Generated posts and annotations are saved with timestamps to track different experimental runs.

## How to run this example

1. Clone this repo
2. Navigate to downloaded folder and create new venv
```
python -m venv liw-env
```
3. Activate venv
```
# mac/linux
source eval-env/bin/activate

# windows
.\eval-env\Scripts\activate.bat
```
4. Install dependencies
```
pip install -r requirements.txt
```
5. Run streamlit app
```
streamlit run annotation_app.py
```