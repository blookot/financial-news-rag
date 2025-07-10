# Chatbot on financial news
Demo of a chatbot querying financial news RSS feeds using Elastic RAG and LLM

This project is a financial news analysis application that uses a RAG (Retrieval-Augmented Generation) architecture. It periodically fetches articles from RSS feeds, indexes them in Elasticsearch using semantic embeddings, and leverages a Large Language Model (LLM) to synthesize information and answer user queries through a Streamlit interface.

## Architecture

The data and processing flow is as follows:

1.  **Logstash**: A Logstash pipeline subscribes to several financial RSS feeds (Le Figaro, Le Monde, BFM, etc.) using the `logstash-input-rss` plugin and is intended to keep running in background.
2.  **Elasticsearch**: The collected articles are sent to an Elasticsearch index.
      * A Machine Learning model (`.multilingual-e5-small`) generates embeddings (semantic vectors) for the titles and content of the articles.
      * The `financial-news-semantic` index is configured to use these embeddings, enabling advanced semantic search capabilities.
3.  **Streamlit & LLM**:
      * A user interface developed with Streamlit allows users to ask questions in natural language.
      * The application queries Elasticsearch using a hybrid search (semantic + keyword) with RRF (Reciprocal Rank Fusion) to find the most relevant articles.
      * The content of these articles is injected into a prompt sent to the Azure OpenAI API.
      * The LLM (GPT-4o) generates a concise and factual summary, citing its sources, which is then displayed to the user.

-----

## Prerequisites

Before you begin, you will need the following:

  * **Elasticsearch & Kibana**. For simplicity, we used an Elastic Cloud deployment but you can use any cluster as long as you have master, data & ML nodes.
  * An **Azure account** with access to the **Azure OpenAI Service** and a deployed `gpt-4o` model.
  * **Python** (version 3.8 or higher).
  * **Logstash** installed locally.

The project was tested with version 8.18.

-----

## Step-by-Step Installation Guide

Follow these steps in order to deploy and run the project.

### 0\. Clone me!

    ```bash
    git clone https://github.com/blookot/financial-news-rag
    cd financial-news-rag
    ```

### 1\. Elasticsearch Setup

The first step is to configure your Elasticsearch cluster to store and search the articles.

1.  **Deploy the ML Model**:

      * In your Elastic Cloud console, navigate to **Machine Learning \> Trained Models**.
      * Click **Download Model** and select the `.multilingual-e5-small` model.
      * Start the model once the download is complete.

2.  **Run the Dev Tools Script**:

      * Open Kibana and go to **Dev Tools**.
      * Copy the contents of the `devtools.json` file and execute each command step-by-step. This script will:
          * Create an inference endpoint (`e5-inference-endpoint`) for the e5 ML model.
          * Create the `financial-news-semantic` index with the correct mapping for semantic search.

### 2\. Data Ingestion with Logstash

This step configures Logstash to fetch RSS feeds and send them to Elasticsearch.

1.  **Install the RSS Plugin**:
    Open a terminal and run the following command from your Logstash installation directory:

    ```bash
    ./bin/logstash-plugin install logstash-input-rss
    ```

2.  **Set Environment Variables**:
    You will need the service URL and credentials for your Elasticsearch cluster. Of course, you can (should!) set a specific user (not elastic).

    ```bash
    export ES_HOST="<YOUR_ELASTIC_CLUSTER_URL>"
    export ES_USER="elastic"
    export ES_PASSWORD="<YOUR_ELASTIC_PASSWORD>"
    ```

3.  **Run Logstash**:
    Run Logstash with the provided configuration file. Make sure the path to the `rss-feed.conf` file is correct, or copy this file at the root of the logstash directory.

    ```bash
    ./bin/logstash -f /path/to/your/project/rss-feed.conf
    ```

    Logstash will now start ingesting articles every 10 minutes and indexing them in Elasticsearch. You can verify that documents are arriving in Kibana \> Discover.

### 3\. Streamlit Application Setup

The final step is to configure and launch the web interface.

1.  **Clone the Project and Prepare the Python Environment**:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables**:
    Configure the variables to connect the application to Azure OpenAI and your Elasticsearch cluster.

    ```bash
    # Variables for Azure OpenAI
    export AZURE_OPENAI_ENDPOINT="<YOUR_AZURE_OPENAI_ENDPOINT>"
    export AZURE_OPENAI_API_KEY="<YOUR_AZURE_API_KEY>"
    export OPENAI_API_VERSION="2024-08-01-preview"
    export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o" # or your deployment name

    # Variables for Elasticsearch (same as for Logstash)
    export local_es_url="${ES_HOST}"
    export local_es_user="${ES_USER}"
    export local_es_pwd="${ES_PASSWORD}"
    export local_es_index="financial-news-semantic"
    ```

### 4\. Running the Application

Once all configurations are complete, you can launch the Streamlit application:

```bash
streamlit run fin-news-streamlit.py
```

Open your browser to the provided address (usually `http://localhost:8501`) to start querying financial news.

-----

## Final thoughts

You will note that this project was made by a french guy! The feeds are in French, the index mapping specifies a french analyzer for text fields and the choice of e5 (rather than ELSER that performs very well) is for multilingual support!<br/>
However, you can adapt the code for ELSER and delete the french analyzer in the mapping.

If you want to add/change the RSS feeds listed in the logstash config file, you might want to check RSS 2.0 compliance of the feed at: https://validator.w3.org/feed/<br/>
And of course, check the Logstash logs to see if the RSS feed is properly read.

-----

## Authors

* **Vincent Maury** - *Initial commit* - [blookot](https://github.com/blookot)

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE.md](LICENSE.md) file for details
