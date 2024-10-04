Environment setup:
conda create -p venv/ python==3.11  # or use an existing env
conda activate venv/                # or activate an existing env
pip3 install -r requirements.txt

Run server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

More details to come.