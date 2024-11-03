# Project Setup and Instructions

## Environment Setup

1. Create a new conda environment (or use an existing one):

    ```sh
    conda create -p venv/ python==3.11
    conda activate venv/
    ```

2. Install the required dependencies:

    ```sh
    pip3 install -r requirements.txt
    ```

## Running the Server

To start the server, run the following command:

```sh
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Create notebooks at top level folder

Webpage in side app/ folder

Please commit working code

More details to come
