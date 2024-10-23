"""
From a list of pubmed_id in paper/pubmed_ids.txt and the already downloaded xml and free pdf 
get the resulting failed and paid to paper/manual_download_pubmed_ids.txt

"""
from pathlib import Path
from .utils import load_txt_file, remove_empty_file, generator_sub_list
from tqdm import tqdm
import xml.etree.ElementTree as ET
import asyncio
import httpx
import shutil
import os
from httpx import ConnectTimeout, RemoteProtocolError, ReadTimeout, ConnectError, ReadError
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_random

@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=0.5))
async def download_scholar(client, pubmed_id):
    params = {
        'fields': 'title,abstract',

    }
    headers = {
        'X-API-KEY': "XX",
    }
    base_url = f'https://api.semanticscholar.org/graph/v1/paper/PMID:{pubmed_id}'
    response = await client.get(
        base_url,
        params=params,
        headers=headers
    )
    try:
        data = response.json()
        return data
    except Exception as e:
        print(response, e, pubmed_id)
        pass
    return None


@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=0.5))
async def download_pubmed(client, pubmed_id):
    # Couldn't find the pubmed record

    # With this url, it works almost directly with JATS ETL parsing
    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    url = '%sefetch.fcgi?db=pubmed&id=%s&retmode=xml&api_key=XX' % (base_url, pubmed_id)
    page = await client.get(url)
    
    if page.status_code == 429:
        raise ConnectTimeout("error 429")
    try:
        xml_abstract = ET.fromstring(page.content)
        #For compatibility with JATS ETL parsing
        xml_abstract =  ET.ElementTree(xml_abstract.findall('PubmedArticle')[0])
        return xml_abstract
    except Exception as e:
        print(page.content, e, pubmed_id)
        pass
    return None

async def download(client, pubmed_id, abstract_path, backup_path, use_backup, overwrite):
    filepath = abstract_path / f"{pubmed_id}.xml"
    backup_filepath = backup_path / f"{pubmed_id}.xml"
    backup_filepath = backup_filepath.resolve()

    if not overwrite and filepath.exists() and filepath.stat().st_size != 0:
        return None
    else:
        if filepath.exists():
            filepath.unlink()

    if use_backup and not overwrite:
        if backup_filepath.exists() and backup_filepath.stat().st_size != 0:
            os.symlink(backup_filepath, filepath)
            return None

    xml, json = await asyncio.gather(download_pubmed(client, pubmed_id), download_scholar(client, pubmed_id))
    if "code" in json:
        print(json, pubmed_id) 
    if xml is None:
        if json is None or 'abstract' not in json or json['abstract'] is None:
            print(f"Could not find pubmed and semantic scholar {pubmed_id}")
            return None
        root = ET.Element('PubmedArticle')
        MedlineCitation = ET.SubElement(root, 'MedlineCitation')
        PMID =  ET.SubElement(MedlineCitation, 'PMID')
        PMID.text = str(pubmed_id)
        Article =  ET.SubElement(MedlineCitation, 'Article')
        AuthorList = ET.SubElement(Article, 'AuthorList')
        AuthorList.text = "[]"
        PublicationTypeList = ET.SubElement(Article, 'PublicationTypeList')
        PublicationType = ET.SubElement(PublicationTypeList, 'PublicationType')
        PublicationType.text = ''
        Abstract =  ET.SubElement(Article, 'Abstract')
        xml = ET.ElementTree(root)
    else:
        Article = xml.find('MedlineCitation').find('Article')
        Abstract = Article.find('Abstract')
        
    if 'title' in json and json['title'] is not None:
        try:
            try:
                Article.remove(Article.find("ArticleTitle"))
            except:
                pass
            ArticleTitle = ET.SubElement(Article, 'ArticleTitle')
            ArticleTitle.text = json['title']
        except:
            pass
    if 'abstract' in json and json['abstract'] is not None:
        try:
            try:
                AbstractText = ET.SubElement(Abstract, 'AbstractText')
            except:
                pass
            Abstract.remove(Abstract.find("AbstractText"))
            AbstractText.text = json['abstract']
        except:
            pass
    xml.write(backup_filepath)
    os.symlink(backup_filepath, filepath)

async def bash_download(
        pubmed_ids_path: Path = Path("../paper/pubmed_ids.txt"),
        XML_path: Path = Path("../paper/XML/"),
        abstract_path: Path = Path("../paper/ABSTRACT/"),
        backup_path: Path = Path("../backup/ABSTRACT/"),
        use_backup: bool=True,
        overwrite: bool=False,
        sample: bool=False,
        window=10 #should stay 10 because of request api limit 
        ):
    abstract_path.mkdir(parents=True, exist_ok=True)
    pubmed_ids = load_txt_file(pubmed_ids_path)
    if sample:
        pubmed_ids = pubmed_ids[:100]
    xml_ids = [p.stem for p in XML_path.glob('*.xml')]
    pubmed_ids = list(set(pubmed_ids) - set(xml_ids))
    remove_empty_file(abstract_path)

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=60.0)) as client:
        for pubmed_ids_sample in tqdm(generator_sub_list(pubmed_ids, window = window, verbose=False), total=len(pubmed_ids)//window):
            tasks = []
            for pubmed_id in pubmed_ids_sample:
                tasks.append(
                    asyncio.ensure_future(
                        download(
                            client,
                            pubmed_id,
                            abstract_path=abstract_path,
                            backup_path=backup_path,
                            use_backup=backup_path,
                            overwrite=overwrite
                        )
                    )
                )
            tasks.append(asyncio.sleep(1))
            _ = await asyncio.gather(*tasks)
    remove_empty_file(abstract_path)

if __name__ == "__main__":
    from jsonargparse import CLI
    asyncio.run(CLI(bash_download))
