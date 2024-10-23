from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup
from .utils import load_txt_file, fetch_summary, remove_empty_file, generator_sub_list, FAILING_PUBMED_SEARCH_IDS
import asyncio
import httpx
from httpx import ConnectTimeout, RemoteProtocolError, ReadTimeout, ConnectError, ReadError
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_random
import subprocess
import os
import shutil

NB_MAX_ENTREZ = 1000

def fetch_pubmed_ids(
        query='"ion channel" OR ("protein"[All Fields] AND (channel or ion)) OR "neurotransmitter" OR "cell membrane" OR "membrane potential" OR "action potential" OR (channel AND (ion OR sodium OR calcium OR potassium OR voltage)) OR ((patch OR voltage) AND clamp)',
        saving_path=Path(os.getenv('AI_DATA')) / "pubmed_ids.txt"
    ):
    """fetch all pubmed ids an save it to a txt file

    Args:
        query (str, optional): _description_. Defaults to '"ion channel" OR ("protein"[All Fields] AND (channel or ion)) OR "neurotransmitter" OR "cell membrane" OR "membrane potential" OR "action potential" OR (channel AND (ion OR sodium OR calcium OR potassium OR voltage)) OR ((patch OR voltage) AND clamp)'.
        saving_path (_type_, optional): _description_. Defaults to Path(os.getenv('AI_DATA'))/"pubmed_ids.txt".
    """
    if saving_path.exists():
        saving_path.unlink()
    else:
        saving_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.call(f"esearch -db pubmed -query '{query}' | efetch -format uid >> {saving_path}", shell=True)


async def bash_download(
        pubmed_ids_path: Path = Path("../paper/pubmed_ids.txt"),
        XML_path: Path = Path("../paper/XML/"),
        backup_path: Path = Path("../backup/XML/"),
        use_backup: bool=True,
        overwrite: bool=False,
        sample: bool=False,
        window=100
        ):
    XML_path.mkdir(parents=True, exist_ok=True)
    backup_path.mkdir(parents=True, exist_ok=True)
  
    pubmed_ids = load_txt_file(pubmed_ids_path)
    if sample:
        pubmed_ids = pubmed_ids[:100]
    
    
    pubmed_ids = list(set(pubmed_ids) - set(FAILING_PUBMED_SEARCH_IDS))

    # fetch summary because download needs pmc_id not pmd_id
    # Due to summary error: UID=24513395: cannot get document summary
    for pubmed_id in FAILING_PUBMED_SEARCH_IDS:
        if pubmed_id in pubmed_ids:
            pubmed_ids.remove(pubmed_id)

    t = tqdm(total=len(pubmed_ids)//window)

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=60.0)) as client:
        for i, pubmed_ids_sample in enumerate(generator_sub_list(pubmed_ids, window = NB_MAX_ENTREZ, verbose=False)):
            summary = fetch_summary(pubmed_ids_sample)
            summary = [s["ArticleIds"] for s in summary]
            for summary_sample in generator_sub_list(summary, window = window, verbose=False):
                tasks = []
                for s in summary_sample:
                    tasks.append(
                        asyncio.ensure_future(
                            download(
                                client,
                                s, 
                                XML_path=XML_path,
                                backup_path=backup_path,
                                use_backup=use_backup,
                                overwrite=overwrite
                            )
                        )
                    )
                tasks.append(asyncio.sleep(1))
                _ = await asyncio.gather(*tasks)
                t.update()

    remove_empty_file(XML_path)

@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=0.5))
async def download(client, article, XML_path, backup_path, use_backup, overwrite):
    # Couldn't find the pubmed record
    if article is None or "pmc" not in article:
        return None

    filepath = XML_path / f"{article['pubmed'][0]}.xml"
    backup_filepath = backup_path / f"{article['pubmed'][0]}.xml"
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


    # With this url, it works almost directly with JATS ETL parsing
    url = f'https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{article["pmc"][3:]}&metadataPrefix=pmc'
    page = await client.get(url)
    if page.status_code == 429:
        raise ConnectTimeout("error 429")
    try:
        xml_paper = BeautifulSoup(page.content, "xml")
        #For compatibility with JATS ETL parsing
        xml_paper = xml_paper.find_all('article')[0]
        if len(xml_paper.find_all('body')[0].find_all('sec')) < 2:
            return None
        # ETL parsing is excpecting only this 2 attributes
        xml_paper.attrs = {key: value for key, value in xml_paper.attrs.items() if key in ["xmlns:xlink", "article-type", "xmlns:ali", "xmlns:mml"]}
        with open(backup_filepath, 'w') as f:
            f.write(xml_paper.prettify().replace('\n', ''))
        os.symlink(backup_filepath, filepath)
    except Exception as e:
        #print(page, e)
        pass
    #os.system(f"""wget -U "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)" -nc --no-verbose --quiet -O {filename} {url}""")
    #if filename.stat().st_size == 0 or not is_xml_complete(filename):
    #    filename.unlink()

    