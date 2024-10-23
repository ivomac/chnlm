from Bio import Entrez
import time
import requests
from requests.adapters import HTTPAdapter, Retry
from collections import OrderedDict
import os
from pathlib import Path
from .query import QUERY

Entrez.email =  'adrien.journe@epfl.ch' # Replace with your email


FAILING_PUBMED_SEARCH_IDS = os.getenv('FAILING_PUBMED_IDS',
        "38109583,26913144,38176796,34836915,4371437,37755572,4607849,24513395,25020364,29356487,37698380,37721218,35969321,37802972,37807464,30006437,35559981,35929290,38176807").split(",")


def valid_fail_suffix(path, index_name, failed):
    if index_name not in list(QUERY.keys()):
        return path
    if failed:
        return path / "fail"
    else:
        return path / "valid"
    
def get_path(index_name, document_type, failed=False):
    if document_type == "pdf":
        return get_pdf_path(index_name, failed)
    if document_type == "xml":
        return get_xml_path(index_name, failed)
    if document_type == "abstract":
        return get_abstract_path(index_name, failed)
    if document_type == "tei":
        return get_tei_path(index_name, failed)
    return get_pubmed_ids_path(index_name)

    
def get_pubmed_ids_path(index_name):
    path = Path(os.getenv('AI_DATA')) / index_name / "pubmed_ids.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def get_xml_path(index_name, failed=False):
    path = Path(os.getenv('AI_DATA')) / index_name / "XML"
    path = valid_fail_suffix(path, index_name=index_name, failed=failed)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_abstract_path(index_name, failed=False):
    path = Path(os.getenv('AI_DATA')) / index_name / "ABSTRACT"
    path = valid_fail_suffix(path, index_name=index_name, failed=failed)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_pdf_path(index_name, failed=False):
    path = Path(os.getenv('AI_DATA')) / index_name / "PDF" 
    path = valid_fail_suffix(path, index_name=index_name, failed=failed)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_tei_path(index_name, failed=False):
    path = Path(os.getenv('AI_DATA')) / index_name / "TEI" 
    path = valid_fail_suffix(path, index_name=index_name, failed=failed)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_with_retry(url):
    s = requests.Session()

    retries = Retry(total=10,
                    backoff_factor=2,
                    status_forcelist=[ 500, 502, 503, 504 ])

    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))

    response = s.get(url)

    return response

def fetch_summary(id_list:list):
    """Fetch information about articles

    Args:
        id_list (list): PUBMED ids
    """
    results = []
    i = 0
    j = min(2000, len(id_list))
    while i<len(id_list):
        error = True
        while error:
            try:
                handle = Entrez.esummary(
                    db='pubmed',
                    retmode='xml',
                    id=','.join(id_list[i:j])
                )
                result = Entrez.read(handle)
                error = False
            except Exception as e:
                print(e, 'summary')
                time.sleep(2)
                result = {}
        results.extend(result)
        i = j
        j = min(i + 2000, len(id_list))
    return results

def load_txt_file(path):
    pubmed_ids = []
    with open(path, 'r') as f:
        for line in f.readlines():
            pubmed_ids.append(line[:-1].rstrip())
    return list(OrderedDict.fromkeys(pubmed_ids))

def save_txt_file(lst, path):
    with open(path, 'w') as f:
        for elem in lst:
            f.write(elem)
            f.write('\n')
            
def remove_empty_file(path, min_size=0):
    for filename in path.glob('*.*'):
        if filename.stat().st_size <= min_size:
            filename.unlink()

def generator_sub_list(lst, window, verbose=True):
    i = 0
    len_lst = len(lst)
    nb_rep = len_lst//window+1
    while i<len_lst:
        if verbose:
            print(f'Sampling: {1 + i//window}/{nb_rep}, done: {i}')
        yield lst[i:i+window]
        i+=window