import os
from typing import Any
from pathlib import Path
import re
import shutil
import logging
import hashlib
import os
import re
from typing import Any
import shutil
from requests.exceptions import ConnectionError
import re
import asyncio
from elasticsearch import ApiError
from scholarag.document_stores import BaseSearch, ElasticSearch, OpenSearch
from scholarag.document_stores.elastic import (
    MAPPINGS_PARAGRAPHS as ELASTICSEARCH_MAPPINGS_PARAGRAPHS,
)
from scholarag.document_stores.elastic import SETTINGS as ELASTICSEARCH_SETTINGS
from scholarag.document_stores.open import (
    MAPPINGS_PARAGRAPHS as OPENSEARCH_MAPPINGS_PARAGRAPHS,
)
from scholarag.document_stores.open import SETTINGS as OPENSEARCH_SETTINGS
from elasticsearch.helpers import BulkIndexError as ESBulkIndexError
from opensearchpy.exceptions import TransportError
from opensearchpy.helpers import BulkIndexError as OSBulkIndexError


from scholarag.ds_utils import ds_upload, get_files, setup_parsing_ds

logger = logging.getLogger(__name__)

def get_dbsearch(db_url:str, user:str=None, password:str=None):
    host, _, port = db_url.rpartition(":")
    document_store = (
        ElasticSearch(
            host=host,
            port=port,
            user=user,
            password=password,
            use_ssl_and_verify_certs=False,
        )  # type: ignore
        if user is not None
        else ElasticSearch(host=host, port=port, use_ssl_and_verify_certs=False)  # type: ignore
    )
    mappings = ELASTICSEARCH_MAPPINGS_PARAGRAPHS
    settings = ELASTICSEARCH_SETTINGS

    return document_store, mappings, settings


def post_processing(txt):
    txt = re.sub(re.compile("Na(?:\s|\(|_)*v(?:\s|\)|_)*([1-9])", re.IGNORECASE),  r"Nav\1", txt)
    txt = re.sub(re.compile("K(?:\s|\(|_)*v(?:\s|\)|_)*([1-9])", re.IGNORECASE),  r"Kv\1", txt)
    txt = re.sub(re.compile("Ca(?:\s|\(|_)*v(?:\s|\)|_)*([1-9])", re.IGNORECASE),  r"Cav\1", txt)
    txt = re.sub("\s\s+", " ", txt)
    return txt

def get_sentences(par):
    sentences_split = re.split('(\.)\s([A-Z])', par)
    if len(sentences_split) == 1:
        return [par]
    sentences = [sentences_split[0] + sentences_split[1]]
    for i in range(2, len(sentences_split), 3):
        sentences.append(''.join(sentences_split[i:i+3]))
    return sentences

def split_json(json_file, max_length, min_length=20):
    split_file = json_file.copy()

    split_file["title"] = post_processing(split_file["title"])

    def split_paragraph(par):
        nb_words = len(re.findall(r'\w+', par))
        if nb_words <= max_length:
            return [par]

        sentences = get_sentences(par)
        sentence_nb_words = [len(re.findall(r'\w+', s)) for s in sentences]
        nb_splits = round(nb_words / max_length)
        mean_len = nb_words / nb_splits
        i=0
        split_par = []
        nb_words = sentence_nb_words[0]
        new_par = sentences[0]
        for s, nb_s in zip(sentences[1:], sentence_nb_words[1:]):
            if nb_words > min_length and (nb_words + nb_s) > mean_len:
                split_par.append(new_par)
                nb_words = 0 
                new_par = s
            else:
                new_par = new_par + ' ' + s
                nb_words += nb_s
        if new_par != '':
            if nb_words > min_length:
                split_par.append(new_par)
            else:
                split_par[-1] = split_par[-1] + ' ' + new_par
        return split_par
        
    abstract = []
    for par in json_file['abstract']:
        par = post_processing(par)
        abstract.extend(split_paragraph(par))
    split_file['abstract'] = abstract
    section_paragraphs = []
    for section_name, par in json_file['section_paragraphs']:
        par = post_processing(par)
        pars= split_paragraph(par)
        section_paragraphs.extend([[section_name, par] for par in pars])
    split_file['section_paragraphs'] = section_paragraphs
    return split_file


async def check_doc_in(client, index, pubmed_id):
    agg = await client.search(
        index=index,
        query={"match" : {"pubmed_id":str(pubmed_id)}},
        aggs={"sections":{"terms":{"field": "section", "size":1000}}},
        size=0
        )
    agg = agg['aggregations']['sections']['buckets']
    if not agg:
        return 0
    list_sections = [section["key"] for section in agg]
    if "Abstract" in list_sections:
        if len(list_sections)>=2:
            return 2
        return 1
    return 0

async def run(
    path: Path,
    failed_path: Path,
    parser_url: str,
    db_url: str,
    multipart_params: dict[str, Any] | None,
    max_concurrent_requests: int = 10,
    articles_per_bulk: int = 100,
    index: str = "paragraphs",
    db_type: str = "opensearch",
    user: str | None = os.getenv('ES_USERNAME', None),
    password: str | None = os.getenv('ES_PASSWORD', None),
    max_length: int = None,
    min_length: int = None,
    use_ssl: bool = False,
) -> int:
    """Run the article parsing and upload results on ES."""
    # Check the path and iterate to have a list of papers to parse
    if not path.exists():
        raise ValueError(f"The path {path} does not exist.")
    
    ds_client, parsing_service = await setup_parsing_ds(
        db_url,
        db_type,
        user,
        password,
        max_concurrent_requests,
        use_ssl,
    )
    #parsing_service.ignore_errors = False
    batches = get_files(
        path,
        recursive=False,
        match_filename=None,
        articles_per_bulk=articles_per_bulk,
    )
    _, _, parser_type = parser_url.rpartition("/")

    for i, batch in enumerate(batches):
        logger.info(f"Request server to parse batch {i}.")
        results = await parsing_service.arun(
            files=batch,
            url=parser_url,
            multipart_params=multipart_params,
        )
        logger.info("Collecting data to upload to the document store.")
        for j in range(len(batch)):
            if results[j] is not None:
                results[j]['pubmed_id'] = batch[j].stem.split('.')[0]

        if max_length is not None:
            for j in range(len(results)):
                if results[j] is not None:
                    results[j] = split_json(results[j], max_length)
                else:
                    results[j] = None

        upload_bulk = []
        files_failing: list[str] = []
        
        try:
            for k, res in enumerate(results):
                nb_pars = 0
                if res is None:
                    files_failing.append(batch[k])
                    continue
                abstract_already_in = await check_doc_in(ds_client, index,  res['pubmed_id'])
                logger.info(abstract_already_in)
                if (parser_type not in ['grobid_pdf', 'tei_xml']) or (abstract_already_in == 0):
                    for i, abstract in enumerate(res["abstract"]):
                        if min_length is None or len(re.findall(r'\w+', abstract)) > min_length:
                            par = {
                                "_index": index,
                                "_id": hashlib.md5(
                                    (res["uid"] + abstract).encode("utf-8"),
                                    usedforsecurity=False,
                                ).hexdigest(),
                                "_source": {
                                    "article_id": res["uid"],
                                    "section": "Abstract",
                                    "text": abstract,
                                    "paragraph_id": i,
                                    "authors": res["authors"],
                                    "title": res["title"],
                                    "pubmed_id": res["pubmed_id"],
                                    "pmc_id": res["pmc_id"],
                                    "arxiv_id": res["arxiv_id"],
                                    "doi": res["doi"],
                                    "date": res["date"],
                                    "journal": res["journal"],
                                    "article_type": res["article_type"],
                                },
                            }
                            upload_bulk.append(par)
                            nb_pars += 1

                for ppos, (section, text) in enumerate(res["section_paragraphs"]):
                    if min_length is None or len(re.findall(r'\w+', text)) > min_length:
                        par = {
                            "_index": index,
                            "_id": hashlib.md5(
                                (res["uid"] + text).encode("utf-8"), usedforsecurity=False
                            ).hexdigest(),
                            "_source": {
                                "article_id": res["uid"],
                                "section": section,
                                "text": text,
                                "paragraph_id": ppos + len(res["abstract"]),
                                "authors": res["authors"],
                                "title": res["title"],
                                "pubmed_id": res["pubmed_id"],
                                "pmc_id": res["pmc_id"],
                                "arxiv_id": res["arxiv_id"],
                                "doi": res["doi"],
                                "date": res["date"],
                                "journal": res["journal"],
                                "article_type": res["article_type"],
                            },
                        }
                        upload_bulk.append(par)
                        nb_pars += 1
            indices = [index for _ in range(len(batch))]
            files_failing = await ds_upload(
                filenames=batch,
                results=results,
                ds_client=ds_client,
                min_paragraphs_length=None,
                max_paragraphs_length=None,
                indices=indices,
            )
        except (ApiError, ESBulkIndexError, TransportError, OSBulkIndexError):
            files_failing = batch

        for file in files_failing:
            logger.info(f"Dumping failing files to {failed_path.resolve()}")
            file.rename(failed_path / file.name)
    await ds_client.close()
    logger.info("Done.")


    return 0
