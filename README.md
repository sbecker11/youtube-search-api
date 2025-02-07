# Overview of the YouTube Search API project

This docker-compose project creates a local-dynamodb image that runs in a localstack image on local DockerDesktop. `Dockerfile` and `docker-compose.yaml` reside at project-root, and are used to deploy assets to DockerDesktop.

QueryEngine in `src/query_engine.py` sends a variety of RESTful search queries to the YouTubeMetadataAPI. Query `request` and `response` data access operations are handled by the YouTubeStorage object. Example query response data may be found in /data/query_response_head.json and query_response_item.json

Search query requests and responses are stored in the Responses dynamoDb tables by YouTubeStorage in `src/youtube_storage.py`. Each response record is given a unique primary key named `response_id` and stored in the Dynamo `Responses` table. All snippets associated with a response are stored in a `Snippets` table and refer to foreign key `response_id`. Dyanamo table definitions for these tables reside at `/data/responses_table_config.json` and `/data/snippets_table_config.json`

YouTubStoreageApi from `src/youtube_searcher_app.py` uses FastAPI to handle queries made by project users against YouTubeStorage. OpenAI documentation is created during `docker-compose up --build` and resides at `/docs`.

QueryScanner in `src/query_scanner.py` is a singleton object that uses `croniter` and `schedule` to run a batch of queries to the YouTubeAPI via QueryEngine. The set to queries and the cron schedule are stored at `/data/query_scanner_config.json`.

Credentials for YouTube and AWS are stored in a local `.env` file, which is never uploaded to the remote github repo.

The structure of the `.env` file is:
```text
YOUTUBE_API_KEY=*****
AWS_ACCESS_KEY_ID=*****
AWS_SECRET_ACCESS_KEY_ID=*****
AWS_DEFAULT_REGION=us-west-2
PYTHONPATH=src:tests
DYNAMODB_URL=http://localstack:4566
RESPONSES_CONFIG_PATH=./data/responses_table_config.json
SNIPPETS_CONFIG_PATH=./data/snippets_table_config.json
QUERY_SCANNER_CONFIG_PATH=./data/query_scanner_config.json
MAX_QUERIES_PER_SCAN=100
```

Docker configuration files are found at project root. Python source modules are found at project root under the `src` directory. Pytest modules are found in `/tests` OpenAPI documentation files are found in `/docs`.

important links:
http://localhost:8000 link to the YouTubeSearcherApp

Object Relationships

    User --------------- uses YouTubeSearcherApp URL
    User --------------- queries data --------------------- YouTubeSearcherApp
app YouTubeSearcherApp -- queries data in ------------------ YouTubeStorage
    YouTubeStorage ----- uses AWS access keys in .env
    QueryEngine -------- uses YOUTUBE_API key in .env
    QueryEngine -------- sends request to ----------------- YouTube-Metadata-API (external)
    QueryEngine -------- saves request+response to -------- YouTubeStorage
app QueryScanner ------- uses /data/query_scanner_config.json
app QueryScanner ------- calls QueryEngine

Project Structure:
```tree
.
├── README.md
├── data
│   ├── query_response_head.json
│   ├── query_response_item.json
│   ├── query_scanner_config.json
│   ├── responses_table_config.json
│   └── snippets_table_config.json
├── data_processor
│   ├── Dockerfile
│   └── app.py
├── docker-compose.yml
├── jest.config.js
├── localstack.pid
├── requirements.txt
├── scripts
│   └── run-pytest
├── src
│   ├── Dockerfile
│   ├── __init__.py
│   ├── query_engine.py
│   ├── query_scanner.py
│   ├── youtube_storage.py
│   ├── youtube_searcher_app.py
│   └── youtube_table.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_conftest.py
    ├── test_query_engine.py
    ├── test_query_scanner.py
    ├── test_youtube_storage.py
    ├── test_youtube_searcher_app.py
    └── test_youtube_table.py
```

# YouTube Search API

## Verifying Docker Desktop is Running

To verify that Docker Desktop is running, you can follow these steps:

1. **Check Docker Desktop Application**: Open the Docker Desktop application on your computer. If it is running, you should see the Docker icon in your system tray (Windows) or menu bar (Mac).

2. **Use Command Line**: Open a terminal and run the following command to check the status of Docker:

```sh
docker info
```

If Docker Desktop is running, this command will display detailed information about your Docker installation, including the server version, storage driver, and other configuration details.

3. **Check Docker Services**: You can also list the running Docker containers to ensure that your services are up and running:

```sh
docker ps
```

This command will display a list of all running containers, including their container IDs, names, and status.

## Running LocalStack with DynamoDB

To start the LocalStack service with DynamoDB, use the following command:

```sh
docker-compose -f docker-compose-dynamodb-only.yml up
```

To stop the services, use:

```sh
docker-compose -f docker-compose-dynamodb-only.yml down
```

YouTube Open AI Specification

https://developers.google.com/youtube/v3/docs
 https://www.googleapis.com/youtube/v3

Search Result Spec
JSON structure shows the format of a search result
https://developers.google.com/youtube/v3/docs/search

YouTubeAPIWrapper
git@github.com:pdrm83/youtube_api_wrapper.git

## Search Videos
```python
from youtube_easy_api.easy_wrapper import *

easy_wrapper = YoutubeEasyWrapper()
easy_wrapper.initialize(api_key=API_KEY)
results = easy_wrapper.search_videos(search_keyword='python', order='relevance')
order_id = 1
video_id = results[order_id]['video_id']

print(video_id)
'_uQrJ0TkZlc'
```

### Extract Metadata
```python
from youtube_easy_api.easy_wrapper import *

easy_wrapper = YoutubeEasyWrapper()
easy_wrapper.initialize(api_key=API_KEY)
metadata = easy_wrapper.get_metadata(video_id='rdjnkb4ONWk')

print(metadata['title'])
'The Pink Panther Show Episode 59 - Slink Pink'

print(metadata['statistics']['likeCount'])
285373
```



### Docker build command
`docker compose up --build`

### Run scanner command
```
APP_CONTAINER_ID=$(docker ps | grep "youtube-search-api-app" | awk '{print $1}')
echo "$APP_CONTAINER_ID"
docker exec -it $APP_CONTAINER_ID python run_scanner.py
```

### API Endpoints
`http://localhost:5000/headers` Endpoint to query the query headers stored in dynamodb
`http://localhost:5000/items` Endpoint to query the items stored in dynamodb


### API Documentation
`http://localhost:5000/docs` Swagger UI to access the interactive Swagger UI documentation
`http://localhost:5000/redoc` ReDoc to access the clean and readable ReDoc documentation

