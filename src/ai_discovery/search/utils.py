from Bio import Entrez
import time
import json
Entrez.email =  'adrien.journe@epfl.ch' # Replace with your email

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

def search(query:str, max_retrieval=100):
    """Query all possible match form pubmed.
    Condition for match:
        - match query

    Args:
        query (str): keywords to query
    """
    #query += " NOT (Review[Publication Type])"
    #query += f"AND ({PROMINENT_JOURNAL[0]}[jour]"
    #for pj in PROMINENT_JOURNAL:
    #    query += f" OR {pj}[jour]"
    #query += ")"
    error = True
    while error:
        try:
            handle = Entrez.esearch(
                db='pubmed', 
                sort='relevance', 
                retmax=str(max_retrieval),
                retmode='xml', 
                term=query
            )

            results = Entrez.read(handle)
            error = False
        except Exception as e:
            time.sleep(1)
            print(e, query)

    if 'IdList' not in results:
        results['IdList'] = []
    return results

def join_akas(name, akas):
    if akas == '':
        return name
    alias = [name] + [x.strip() for x in akas.split(',')]
    alias = [x.lower() for x in alias]
    #alias = list(set(alias)) #unique
    alias = '" OR "'.join(alias)
    return alias

def get_drug_search_pubmed_query(drug, drug_akas, channel_name, akas_channel):
    return f'("{join_akas(drug, drug_akas)}") AND ("{join_akas(channel_name, akas_channel)}")'

def get_distribution_search_pubmed_query(channel_name, akas_channel):
    return f'(axon OR dendrite OR soma OR subcellular OR location OR distribution) AND ("{join_akas(channel_name, akas_channel)}")'

def get_pubmedids_of_interest(query, max_nb_paper):
    return search(query, max_nb_paper)['IdList']

def get_family(channel_name):
    # ---------------------TRP--------------------------
    # --------TRP subunits------
    # --------TRP channels------
    if channel_name.startswith('TRPA'):
        return '|'.join(['TRP', 'TRPA'])
    if channel_name.startswith('TRPC'):
        return '|'.join(['TRP', 'TRPC'])
    if channel_name.startswith('TRPML'):
        return '|'.join(['TRP', 'TRPML'])
    if channel_name.startswith('TRPM'):
        return '|'.join(['TRP', 'TRPM'])
    if channel_name.startswith('TRPP'):
        return '|'.join(['TRP', 'TRPP'])
    if channel_name.startswith('TRPV'):
        return '|'.join(['TRP', 'TRPV'])
    # ---------------------Hcn--------------------------
    # --------Hcn subunits------
    # --------Hcn channels------
    if channel_name.startswith('HCN'):
        return '|'.join(['HCN'])
    # ---------------------Ca--------------------------
    # --------Ca subunits------
    if channel_name.startswith('ClCK'):
        return '|'.join(['Cl', 'ClCK'])
    if channel_name.startswith('ClIC'):
        return '|'.join(['Cl', 'ClIC'])
    if channel_name.startswith('ClC'):
        return '|'.join(['Cl', 'ClC'])
    # ---------------------Cl--------------------------
    # --------Cl subunits------
    if channel_name.startswith('ClCA'):
        return '|'.join(['Cl', 'ClCA subunits'])
    # --------Cl channels------
    if channel_name.startswith('Cav'):
        return '|'.join(['Cav', channel_name[0:4]])
    # ---------------------Ca--------------------------
    # --------Ca subunits------
    if channel_name.startswith('ClCK'):
        return '|'.join(['Cl', 'ClCK'])
    if channel_name.startswith('ClIC'):
        return '|'.join(['Cl', 'ClIC'])
    if channel_name.startswith('ClC'):
        return '|'.join(['Cl', 'ClC'])
    # --------Ca channels------
    if channel_name.startswith('Cav'):
        return '|'.join(['Cav', channel_name[0:4]])
    # ---------------------Nav--------------------------
    # --------Nav subunits------
    if channel_name.startswith('Navβ'):
        return '|'.join(['Nav', 'Navβ subunits'])
    # --------Nav channels------
    if channel_name.startswith('Nav1'):
        return '|'.join(['Nav'])
    if channel_name.startswith('NaG'):
        return '|'.join(['Nav'])
    # ---------------------Kv--------------------------
    # --------KV subunits------
    if channel_name.startswith('Kvβ'):
        return '|'.join(['K', 'Kv subunits', 'Kvβ'])
    if channel_name.startswith('KChIP'):
        return '|'.join(['K', 'Kv subunits', 'KChIP'])
    if channel_name.startswith('KCNE'):
        return '|'.join(['K', 'Kv subunits', 'KCNE'])
    
    # --------KCa subunits------
    if channel_name.startswith('BKβ'):
        return '|'.join(['K', 'KCa subunits', 'BKβ'])
    if channel_name.startswith('BKγ'):
        return '|'.join(['K','KCa subunits', 'BKγ'])
    
    # --------Kir subunits------
    if channel_name.startswith('SUR'):
        return '|'.join(['K', 'Kir subunits', 'SUR'])
    # --------Kv channels------
    if channel_name.startswith('Kv'):
        if channel_name[3] == '.':
            return '|'.join([ 'K', 'Kv', channel_name[0:3]])
        else:
            return '|'.join([ 'K', 'Kv', channel_name[0:4]])
    if channel_name.startswith('Kir'):
        return '|'.join(['K', 'Kir'])
    if channel_name.startswith('SK'):
        return '|'.join(['K', 'KCa', 'SK'])
    if channel_name.startswith('Slo'):
        return '|'.join(['K', 'KCa', 'Slo'])
    if channel_name.startswith('TALK'):
        return '|'.join(['K', 'K2P', 'TALK'])
    if channel_name.startswith('TASK'):
        return '|'.join(['K', 'K2P', 'TASK'])
    if channel_name.startswith('THIK'):
        return '|'.join(['K', 'K2P', 'THIK'])
    if channel_name.startswith('TRAAK'):
        return '|'.join(['K', 'K2P', 'TRAAK'])
    if channel_name.startswith('TREK'):
        return '|'.join(['K', 'K2P', 'TREK'])
    if channel_name.startswith('TRESK'):
        return '|'.join(['K', 'K2P', 'TRESK'])
    if channel_name.startswith('TWIK'):
        return '|'.join(['K', 'K2P', 'TWIK'])
    return '|'.join(['others'])


def get_parent(channel_name):
    # ---------------------TRP--------------------------
    # --------TRP subunits------
    # --------TRP channels------
    if channel_name.startswith('TRPA'):
        return 'TRP'
    if channel_name.startswith('TRPC'):
        return 'TRP'
    if channel_name.startswith('TRPML'):
        return 'TRP'
    if channel_name.startswith('TRPM'):
        return 'TRP'
    if channel_name.startswith('TRPP'):
        return 'TRP'
    if channel_name.startswith('TRPV'):
        return 'TRP'
    # ---------------------Hcn--------------------------
    # --------Hcn subunits------
    # --------Hcn channels------
    if channel_name.startswith('HCN'):
        return 'HCN'
    # ---------------------Ca--------------------------
    # --------Ca subunits------
    if channel_name.startswith('ClCK'):
        return 'Cl'
    if channel_name.startswith('ClIC'):
        return 'Cl'
    if channel_name.startswith('ClC'):
        return 'Cl'
    # ---------------------Cl--------------------------
    # --------Cl subunits------
    if channel_name.startswith('ClCA'):
        return 'Cl'
    # --------Cl channels------
    if channel_name.startswith('Cav'):
        return 'Cav'
    # ---------------------Ca--------------------------
    # --------Ca subunits------
    if channel_name.startswith('ClCK'):
        return 'Cl'
    if channel_name.startswith('ClIC'):
        return 'Cl'
    if channel_name.startswith('ClC'):
        return 'Cl'
    # --------Ca channels------
    if channel_name.startswith('Cav'):
        return 'Cav'
    # ---------------------Nav--------------------------
    # --------Nav subunits------
    if channel_name.startswith('Navβ'):
        return 'Nav'
    # --------Nav channels------
    if channel_name.startswith('Nav1'):
        return 'Nav'
    if channel_name.startswith('NaG'):
        return 'Nav'
    # ---------------------Kv--------------------------
    # --------KV subunits------
    if channel_name.startswith('Kvβ'):
        return 'Kv subunits'
    if channel_name.startswith('KChIP'):
        return 'K'
    if channel_name.startswith('KCNE'):
        return 'K'
    
    # --------KCa subunits------
    if channel_name.startswith('BKβ'):
        return '|'.join(['K', 'KCa subunits', 'BKβ'])
    if channel_name.startswith('BKγ'):
        return '|'.join(['K','KCa subunits', 'BKγ'])
    
    # --------Kir subunits------
    if channel_name.startswith('SUR'):
        return '|'.join(['K', 'Kir subunits', 'SUR'])
    # --------Kv channels------
    if channel_name.startswith('Kv'):
        if channel_name[3] == '.':
            return '|'.join([ 'K', 'Kv', channel_name[0:3]])
        else:
            return '|'.join([ 'K', 'Kv', channel_name[0:4]])
    if channel_name.startswith('Kir'):
        return '|'.join(['K', 'Kir'])
    if channel_name.startswith('SK'):
        return '|'.join(['K', 'KCa', 'SK'])
    if channel_name.startswith('Slo'):
        return '|'.join(['K', 'KCa', 'Slo'])
    if channel_name.startswith('TALK'):
        return '|'.join(['K', 'K2P', 'TALK'])
    if channel_name.startswith('TASK'):
        return '|'.join(['K', 'K2P', 'TASK'])
    if channel_name.startswith('THIK'):
        return '|'.join(['K', 'K2P', 'THIK'])
    if channel_name.startswith('TRAAK'):
        return '|'.join(['K', 'K2P', 'TRAAK'])
    if channel_name.startswith('TREK'):
        return '|'.join(['K', 'K2P', 'TREK'])
    if channel_name.startswith('TRESK'):
        return '|'.join(['K', 'K2P', 'TRESK'])
    if channel_name.startswith('TWIK'):
        return '|'.join(['K', 'K2P', 'TWIK'])
    return '|'.join(['others'])