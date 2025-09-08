import os
import streamlit as st # type: ignore
from openai import AzureOpenAI # type: ignore
from elasticsearch import Elasticsearch # type: ignore


# how many results are returned from ES
NB_RESULTS=20


client = AzureOpenAI(
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
    api_key=os.environ['AZURE_OPENAI_API_KEY'],
    api_version=os.environ['OPENAI_API_VERSION']
)

# Connect to Elastic Cloud cluster
def es_connect(es_url, es_user, es_pwd):
    es = Elasticsearch(es_url, basic_auth=(es_user, es_pwd))
    return es

# Search ElasticSearch index and return body and URL of the result
def search(query_text):
    es_url = os.environ['local_es_url']
    es_user = os.environ['local_es_user']
    es_pwd = os.environ['local_es_pwd']
    es = es_connect(es_url, es_user, es_pwd)
    es_index = os.environ['local_es_index']

    query = {
        "size": NB_RESULTS,
        "retriever": {
            "rrf": {
            "retrievers": [
                {
                "standard": {
                    "query": {
                    "semantic": {
                        "field": "message_semantic",
                        "query": query_text
                    }
                    }
                }
                },
                {
                "standard": {
                    "query": {
                    "semantic": {
                        "field": "title_semantic",
                        "query": query_text
                    }
                    }
                }
                },
                {
                "standard": {
                    "query": {
                    "multi_match": {
                        "query": query_text,
                        "fields": [
                        "message",
                        "title"
                        ]
                    }
                    }
                }
                }
            ],
            "rank_window_size": NB_RESULTS
            }
        }
    }

    # run the ES query
    index = es_index
    resp = es.search(index=index,body=query)
    results = resp["hits"]["hits"]

    # prepare context for LLM
    context = ""
    for hit in results:
        source = hit["_source"]
        title = source.get("title", "Titre non disponible")
        message = source.get("message", "Texte non disponible")
        tags = source.get("tags", "Source non disponible")
        published = source.get("published", "Date de publication non disponible")
        link = source.get("link", "Lien non disponible")
        context += f"**Titre:** {title}\n\n**Texte:** {message}\n\n**Source:** {tags}\n\n**Date de publication:** {published}\n\n**Lien:** {link}\n\n---\n\n"
    
    # build LLM prompt
    prompt = f"""
            Tu es un assistant d'analyse financière pour un trader expérimenté. Ta mission est de synthétiser les actualités financières fournies dans le CONTEXTE ci-dessous. Tu dois aller droit au but.

            ### CONSIGNES :
            1.  **Synthèse concise** : dans ta réponse, commence par fournir un résumé des actualités les plus pertinentes en 100 mots. Puis, sous forme de liste à puces, liste les 5 articles les plus pertinents qui détaillent l'actualité.
            2.  **Sources** : varie les sources autant que possible.
            3.  **Source cliquable** : Termine **chaque point** par le lien vers l'article original, formaté en Markdown comme ceci : `[nom de la source](lien url complet)`. Si le lien n'est pas disponible, essaie de l'extraire du message lui-même (qui se termine souvent par un lien URL)
            4.  **Langue** : La réponse doit être exclusivement en **Français**.
            5.  **Factualité** : Base ta réponse **uniquement** sur les informations présentes dans le contexte. N'ajoute aucune information externe.
            6.  **Style** : Utilise un style télégraphique, direct et factuel.
            7.  **Sentiment** : Pour chaque point, indique clairement le sentiment : [Positif], [Négatif] ou [Neutre].
            8.  **Publication** : Vérifie que la date de publication de chaque article source correspond à la demande. Si aucune date n'est mentionnée dans la requête, prends les articles les plus récents en priorité.
            
            ### EXEMPLE DE RÉPONSE ATTENDUE :
            * [Positif] Apple Inc. surperforme le marché suite à l'annonce d'un rachat d'actions massif et d'un partenariat stratégique. [Bloomberg](https://www.bloomberg.com/news/apple-12345)
            * [Négatif] Le CAC 40 est pénalisé par des craintes sur la chaîne d'approvisionnement et la hausse des coûts des matières premières. [Les Echos](https://www.lesechos.fr/news/cac40-54321)

            ### CONTEXTE :
            {context}
    """
    return context, prompt, query


# Generate a response from the LLM based on the given prompt
def chat_with_llm(prompt, query):
    response = client.chat.completions.create(
        model=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'], 
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content

# Streamlit
st.set_page_config(
    page_title="Synthèse d'actualités financières",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Cette application montre l'utilisation d'Elasticsearch pour du RAG."
    }
)
st.header("📈 Synthèse d'actualités financières")
st.write("Posez une question sur l'actualité financière pour obtenir une synthèse basée sur les dernières dépêches.")
st.write("[Documentation Elastic RAG](https://www.elastic.co/fr/solutions/generative-ai/retrieval-augmented-generation-rag)")

# Search bar
with st.form("search_form"):
    user_input = st.text_input("Votre question :", "Quelles sont les nouvelles sur les valeurs technologiques américaines ?")
    submitted = st.form_submit_button("Lancer la recherche")
if submitted:
    with st.spinner("Recherche des articles et génération de la synthèse..."):
        # Search docs
        context, prompt, query = search(user_input)
        # Call LLM
        answer = chat_with_llm(prompt, user_input)
        # Search results. Col1 = ES answer, Col2 = LLM answer
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📄 Documents sources (Elasticsearch)")
            st.markdown(context)
        with col2:
            st.subheader("✨ Synthèse (LLM)")
            st.markdown(answer.strip())
        # Request details
        with st.expander("🔍 Voir la requête Elasticsearch (JSON)"):
            st.json(query)