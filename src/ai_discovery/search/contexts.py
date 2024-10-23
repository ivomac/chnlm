import re
import asyncio
from scholarag.document_stores import ElasticSearch, OpenSearch
from scholarag.services import CohereRerankingService

async def get_contexts(
    ds_client:ElasticSearch|OpenSearch,
    reranking_service:CohereRerankingService,
    pubmed_id:int,
    rerank_sentence:str,
    nb_sections:int
):
    contexts = ds_client.search(
        index='drug_screening',
        size= 100,
        query={"match" : {"pubmed_id": str(pubmed_id)}},
    )
    contexts = contexts["hits"]['hits']
    for context in contexts:
        context['_source']['document_id'] = context['_id']
        del context['_id']
    contexts = [context['_source'] for context in contexts]
    for context in contexts:
        context["text"] = re.sub("\s\s+", " ", context["text"])
    rerank_k = 15
    if len(contexts)>nb_sections:
        contexts, contexts_text, scores, indices = await reranking_service.rerank(
                rerank_sentence,
                contexts,
                nb_sections,
            )
    else:
        indices = tuple(range(len(contexts)))
        scores = None
    return contexts, scores, indices