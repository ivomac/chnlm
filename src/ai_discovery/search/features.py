from .contexts import get_contexts
from .prompt import DRUG_SCREENING_QUERY, DrugMapping
from .sql import record_exist, add_row
from .utils import get_family
import asyncio
import json

def get_metadata(contexts, indices, scores, context_ids):
    metadata = {
        "article_id": contexts[0]["article_id"],
        "ds_document_id": str(contexts[0]["document_id"]),
        "pubmed_id": contexts[0]["pubmed_id"],
        "article_doi": contexts[0]["doi"],
        "article_title": contexts[0]["title"],
        "article_authors": contexts[0]["authors"],
        "article_type": contexts[0]["article_type"],
        "sections": []
    }
    #for context_id in context_ids:
    for context_id in range(len(contexts)):
        context = contexts[context_id]
        metadata["sections"].append({
                "context_id": indices[context_id],
                "reranking_score": (
                    scores[context_id] if scores is not None else None
                ),
                "source_id": context_id,
                "section": context["section"],
                "paragraph": context["text"],
                "selected": context_id in context_ids,
                #"abstract": abstracts[context.get("article_id")],
            }
        )
    return metadata

async def get_effect(chain, pubmed_id, contexts, drug_name, akas_drug, channel_name, akas_channel):
    nb_query_openAI = 0
    nb_query_cohere = 0
    channel_alias = channel_name + f" (a.k.a {akas_channel})" if akas_channel != "" else channel_name
    drug_alias = drug_name + f" ({akas_drug})" if akas_drug != "" else channel_name

    sections = json.dumps({
        f"Section {i}": context["text"] for i, context in enumerate(contexts)
    })

    response = await chain.arun(
        {
            "question": DRUG_SCREENING_QUERY.format(drug_name=drug_alias, channel_name=channel_alias),
            "sections": sections
        }
    )
    return response

def get_format(contexts):
    if not contexts:
        return None
    if len(list(set([context['section'] for context in contexts]))) == 1:
        return 'Abstract'
    return 'Full text'

async def get_features(chain, parser, ds_client, reranking_service, article, drug_name, akas_drug, channel_name, akas_channel, overwrite, nb_sections):
    pubmed_id = article['pubmed'][0]
    doi = article['doi'] if 'doi' in article else None
    record_id, json_output, format_ = record_exist(drug_name, channel_name, pubmed_id)

    nb_query_openAI = 0
    nb_query_cohere = 0

    if overwrite or record_id is None or format_ is None:
        contexts, scores, indices = await get_contexts(
            ds_client=ds_client,
            reranking_service=reranking_service,
            pubmed_id=pubmed_id,
            rerank_sentence=f"Drug testing of {drug_name} on {channel_name}, the activation effect (OPEN (enhance, activate, facilitate, agonist), CLOSE (reduce, block, inhibit, antagonist)), dose/response (molar) and subject (cell line / mouse or rat species).",
            nb_sections=nb_sections
        )
        values = {
            'drug': drug_name, 
            'channel': channel_name,
            'family': get_family(channel_name),
            'pubmed_id': pubmed_id,
            'format': get_format(contexts),
            'output': DrugMapping().model_dump(mode='json'),
            'metadata': {"sections":[]}
        }

        if not contexts:
            add_row(record_id, values)
            return False
        output = await get_effect(chain, pubmed_id, contexts, drug_name, akas_drug, channel_name, akas_channel)
        try:
            output = parser.parse(output)
            json_output = output.model_dump(mode='json')
            values["output"] = json_output
            metadata = get_metadata(contexts, indices, scores, json_output["effect"]["sufficient_sections"] if json_output is not None else [])
            values["metadata"] = metadata
        except:
            print(f"Canot parse {output}")

        add_row(record_id, values)
    if json_output is None:
        return False
    if not isinstance(json_output, dict) or not "effect"  in json_output:
        return False
    if not isinstance(json_output["effect"], dict) or not "sufficient_sections"  in json_output["effect"]:
        return False
    return json_output["effect"]["sufficient_sections"]
    