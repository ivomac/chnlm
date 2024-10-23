"""
From a list of pubmed_id in paper/pubmed_ids.txt and the already downloaded xml for pubmed central,
download the free pdf online got from https://unpaywall.org/products/api, and download to ../paper/pdf.

Features:
1- Possible overwrite parameter:
    - if False: will only download xml not already in paper/xml
"""
from pathlib import Path
import os
import asyncio
import httpx
from httpx import ConnectTimeout, RemoteProtocolError, ReadTimeout, ConnectError, ReadError
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_random
import shutil
from .utils import load_txt_file, generator_sub_list, fetch_summary, remove_empty_file, FAILING_PUBMED_SEARCH_IDS
from tqdm import tqdm
import itertools

NB_CONCURRENT = 250
MIN_SIZE = 10000

@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=1))
async def query_one_unpaywall(client, pubmed_id):
    page = await client.get(f'https://api.unpaywall.org/v2/{pubmed_id}?email=adrien.journe@epfl.ch')
    try:
        return page.json()
    except:
        return {}

@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=1))
async def find_download_pdf(client, article, pdf_path, backup_path, use_backup, overwrite):
   
    filepath = pdf_path / f"{article['pubmed'][0]}.pdf"

    backup_filepath = backup_path / f"{article['pubmed'][0]}.pdf"
    backup_filepath = backup_filepath.resolve()

    if not overwrite and filepath.exists() and filepath.stat().st_size != 0:
        return None
    else:
        if filepath.exists():
            filepath.unlink()

    if use_backup and not overwrite:
        if backup_filepath.exists():
            os.symlink(backup_filepath, filepath)
            return None
 
    if article is None or "doi" not in article:
        return None
   
    info = await query_one_unpaywall(client, article["doi"])

    for key in info:
        if key.endswith('oa_location') and info[key] is not None and "url_for_pdf" in info[key] and info[key]["url_for_pdf"] is not None:
            try:
                url = info[key]["url_for_pdf"] #.replace(' ', '%20').replace('(', '\(').replace(')', '\)')
                pdf = await client.get(url, follow_redirects=True)
                open(backup_filepath, 'wb').write(pdf.content)
            except Exception as e:
                print(e, filepath, info[key]["url_for_pdf"])
                pass
            if backup_filepath.exists():
                if backup_filepath.stat().st_size <= MIN_SIZE: # in bytes
                    backup_filepath.unlink()
                else:
                    os.symlink(backup_filepath, filepath)
                    break
            

sem = asyncio.Semaphore(NB_CONCURRENT)

async def safe_download(**args):
    async with sem:  # semaphore limits num of simultaneous downloads
        return await find_download_pdf(**args)

async def bash_download(
        pubmed_ids_path: Path = Path("../paper/pubmed_ids.txt"),
        XML_path: Path = Path("../paper/XML/"),
        pdf_path: Path = Path("../paper/pdf/"),
        backup_path: Path =  Path("../paper/backup/pdf"),
        use_backup: bool=True,
        overwrite: bool = False,
        sample: bool=False,
        window=1000,
        ):
    
    pdf_path.mkdir(parents=True, exist_ok=True)
    pubmed_ids = load_txt_file(pubmed_ids_path)
    if sample:
        pubmed_ids = pubmed_ids[:100]
    
    xml_ids = [p.stem for p in XML_path.glob('*.xml')]
    pubmed_ids = list((set(pubmed_ids) - set(xml_ids))- set(FAILING_PUBMED_SEARCH_IDS))

    # Due ot summary error: UID=24513395: cannot get document summary
    for pubmed_id in FAILING_PUBMED_SEARCH_IDS:
        if pubmed_id in pubmed_ids:
            pubmed_ids.remove(pubmed_id)
            filename = pdf_path / f"{pubmed_id}.pdf"
            backup_filename = backup_path / f"{pubmed_id}.pdf"
            if backup_filename.exists():
                shutil.copyfile(backup_filename, filename)
                return None
    remove_empty_file(pdf_path, min_size=MIN_SIZE)
    remove_empty_file(backup_path, min_size=MIN_SIZE)
    tasks = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(1000.0, connect=600.0), verify=False) as client:
        for pubmed_ids_sample in tqdm(generator_sub_list(pubmed_ids, window=window, verbose=False), total=len(pubmed_ids)//window):

            blocking_coro = asyncio.to_thread(fetch_summary, id_list=pubmed_ids_sample)
            summary = await blocking_coro

            summary = [s["ArticleIds"] for s in summary]

            for s in summary:
                tasks.append(
                    asyncio.ensure_future(
                        safe_download(
                            client=client,
                            article=s,
                            pdf_path=pdf_path,
                            backup_path=backup_path,
                            use_backup=use_backup,
                            overwrite=overwrite
                        )
                    )
                )
            
            for task in itertools.islice(asyncio.as_completed(tasks), len(tasks)-min(len(tasks), 10*NB_CONCURRENT)):
                await task
            tasks = [task for task in tasks if not task.done()]
        await asyncio.gather(*tasks)
    remove_empty_file(pdf_path, min_size=MIN_SIZE)
    remove_empty_file(backup_path, min_size=MIN_SIZE)

if __name__ == "__main__":
    from jsonargparse import CLI
    #asyncio.run(CLI(main))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(CLI(main))