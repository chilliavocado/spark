Environment setup:
conda create -p venv/ python==3.11  # or use an existing env
conda activate venv/                # or activate an existing env
pip3 install -r requirements.txt

Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Create notebooks at top level folder.
Webpage in side app/ folder

Please commit working code.
 
More details to come.