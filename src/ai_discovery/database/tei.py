from pathlib import Path
import os
import asyncio
import httpx
from httpx import ConnectTimeout, RemoteProtocolError, ReadTimeout, ConnectError, ReadError
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_random
import shutil
from .utils import generator_sub_list, remove_empty_file
from tqdm import tqdm
import itertools

NB_CONCURRENT = 1


@retry(retry=retry_if_exception_type((ConnectTimeout, RemoteProtocolError, ReadTimeout, ValueError, ConnectError, ReadError)), stop=stop_after_attempt(5), wait=wait_random(min=0.1, max=0.5))
async def to_tei(client, grobid_url, pdf_path, tei_path, backup_path, use_backup, overwrite):
    pubmed_id = pdf_path.stem
    filepath = tei_path / f"{pubmed_id}.tei.xml"
    backup_filepath = backup_path / f"{pubmed_id}.tei.xml"
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

    pdf_strm = open(pdf_path, 'rb').read()

    url = f"{grobid_url}/api/processFulltextDocument"
    files = {"input": pdf_strm}
    headers = {"Accept": "application/xml"}
    
    try:
        response = await client.post(
            url=url, files=files, headers=headers, params={}
        )
        if response.status_code == 429:
            raise ConnectTimeout("error 429")
        tei = response.text
        response.raise_for_status()
        with open(backup_filepath, 'w') as f:
            f.write(tei)
        os.symlink(backup_filepath, filepath)
    except Exception as e:
        print(e)
        pass



async def bash_extract(
    pdf_path: Path = Path("../paper/pdf/"),
    tei_path: Path = Path("../paper/tei/"),
    backup_path: Path = Path("../paper/tei/"),
    use_backup: bool = True,
    overwrite: bool = False,
    grobid_url: str = 'http://localhost:8070',
    sample: bool=False,
    window: int=100,
    nb_concurrent: int=NB_CONCURRENT
    ):

    sem = asyncio.Semaphore(nb_concurrent)
    async def safe_download(**args):
        async with sem:  # semaphore limits num of simultaneous downloads
            return await to_tei(**args)

    tei_path.mkdir(parents=True, exist_ok=True)
    
    remove_empty_file(tei_path, min_size=1000)

    pdf_path_list = list(pdf_path.glob('*.pdf'))

    tasks = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(1000.0, connect=60.0), verify=False) as client:
        for pdf_path_sample in tqdm(generator_sub_list(pdf_path_list, window = window, verbose=False), total=len(pdf_path_list)//window):

            for p in pdf_path_sample:
                tasks.append(
                    asyncio.ensure_future(
                        safe_download(
                            client=client,
                            grobid_url=grobid_url,
                            pdf_path=p,
                            tei_path=tei_path,
                            backup_path=backup_path,
                            use_backup=use_backup,
                            overwrite=overwrite
                        )
                    )
                )
            
            for task in itertools.islice(asyncio.as_completed(tasks), len(tasks)-min(len(tasks), 10*nb_concurrent)):
                await task
            tasks = [task for task in tasks if not task.done()]
        await asyncio.gather(*tasks)

    remove_empty_file(pdf_path, min_size=1000)


if __name__ == "__main__":
    from jsonargparse import CLI
    #asyncio.run(CLI(main))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(CLI(main))