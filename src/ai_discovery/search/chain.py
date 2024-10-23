from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
import os
from pathlib import Path
import asyncio
import argparse
from ..database.dbsearch import get_dbsearch
from .utils import get_drug_search_pubmed_query, get_pubmedids_of_interest, fetch_summary
from .prompt import DRUG_SCREENING_PROMPT, DRUG_SCREENING_PARSER
from .channels_drugs import CHANNELS, DRUGS
from .features import get_features
from .sql import create_main_table

from scholarag.services import CohereRerankingService

NB_CONCURRENT=2
NB_MIN_SCREENING=5

sem = asyncio.Semaphore(NB_CONCURRENT)
async def safe_concurrency(**args):
    async with sem:  # semaphore limits num of simultaneous downloads
        return await get_features(**args)


def get_chain(prompt:str, model_name:str="gpt-4o-mini", temperature:float=0., verbose:bool=False):
    llm=ChatOpenAI(
        model_name=model_name,
        temperature=temperature,
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore
        max_tokens=None
    )
    chain = LLMChain(
        llm=llm, prompt=prompt, verbose=True
    )
    return llm, chain

async def run_one_channel_drug(channel_name, drug_name, overwrite):
    create_main_table()

    drug_name, drug_akas = DRUGS[drug_name]["drug_name"], DRUGS[drug_name]["akas_drug"]
    channel_name, akas_to_add_llm, akas_to_add_pubmed = CHANNELS[channel_name]["channel_name"], CHANNELS[channel_name]["akas_to_add_llm"], CHANNELS[channel_name]["akas_to_add_pubmed"]

    print(channel_name, akas_to_add_llm, akas_to_add_pubmed)

    query = get_drug_search_pubmed_query(
        drug=drug_name,
        drug_akas=drug_akas,
        channel_name=channel_name,
        akas_channel=akas_to_add_pubmed
    )
    pubmed_ids = get_pubmedids_of_interest(query, 100)
  
    summaries = fetch_summary(pubmed_ids)
    summaries = [summary["ArticleIds"] for summary in summaries]

    ds_client, _, _= get_dbsearch(
        db_url=os.getenv('ES_HOST'),
        user=os.getenv('ES_USERNAME', None),
        password=os.getenv('ES_PASSWORD', None)
    )

    _, chain = get_chain(
        prompt=DRUG_SCREENING_PROMPT,
        model_name=os.getenv("OPEN_AI_MODEL", "gpt-4o-mini"),
        temperature=0.,
        verbose=True
    )

    reranking_service = CohereRerankingService(  # type: ignore
        api_key=os.getenv("COHERE_API_KEY"), # type: ignore
    )


    if not pubmed_ids:
        await get_features(
                chain=chain,
                parser=DRUG_SCREENING_PARSER,
                ds_client=ds_client,
                reranking_service=reranking_service,
                article={"pubmed":[0], 'doi':''},
                drug_name=drug_name,
                akas_drug=drug_akas,
                channel_name=channel_name,
                akas_channel=akas_to_add_llm,
                overwrite=overwrite,
                nb_sections=6
        )

    tasks = []
    for summary in summaries:
        tasks.append(asyncio.ensure_future(
            safe_concurrency(
                chain=chain,
                parser=DRUG_SCREENING_PARSER,
                ds_client=ds_client,
                reranking_service=reranking_service,
                article=summary,
                drug_name=drug_name,
                akas_drug=drug_akas,
                channel_name=channel_name,
                akas_channel=akas_to_add_llm,
                overwrite=overwrite,
                nb_sections=6
            )
        )
    )
    #results = await asyncio.gather(*tasks)
    nb_screening = 0
    nb_task = 0 
    # iterate over awaitables
    for task in asyncio.as_completed(tasks):
        # get the next result
        result = await task
        nb_task += 1
        if result:
            nb_screening += 1
        if nb_screening == NB_MIN_SCREENING:
            break
    for task in tasks:
        if not task.done():
            task.cancel()
