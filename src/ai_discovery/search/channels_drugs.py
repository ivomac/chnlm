import pandas as pd
import numpy as np
import re
from pathlib import Path
import json
import os


def build_variation(channel_name):
    variations = []
    if channel_name.startswith('Kv'):
       digits = channel_name[2:]
       variations.extend(
           ['K(v)'+digits, 'Kv '+digits, 'Kv('+digits+')', 'K(v) '+digits]
        )
    if channel_name.startswith('Nav'):
       digits = channel_name[3:]
       variations.extend(
           ['Na(v)'+digits, 'Nav '+digits, 'Nav('+digits+')', 'Na(v) '+digits]
        )
    if channel_name.startswith('Kir'):
       digits = channel_name[3:]
       variations.extend(
           ['Kir '+digits, 'Kir('+digits+')']
        )
    if channel_name.startswith('HCN'):
       digits = channel_name[3:]
       variations.extend(
           ['HCN '+digits, 'HCN('+digits+')']
        )
    if channel_name.startswith('Cav'):
       digits = channel_name[3:]
       variations.extend(
           ['Ca(v)'+digits, 'Cav '+digits, 'Cav('+digits+')', 'Ca(v) '+digits]
        )
    common_variations = variations.copy()
    for v in variations:
        if 'β' in v:
          common_variations.append(re.sub('β', '(β)', v))
        if 'α' in v:
          common_variations.append(re.sub('α', '(α)', v))
    return common_variations

def select_alias(alias):
    if alias == '' or alias == np.nan:
        return []
    alias = alias.split(';')
    alias = [a for a in alias if len(a)>3]
    return alias

print()
ionchannels = pd.read_csv(Path(__file__).parent.resolve()/'ionchannels.csv')
ionchannels = ionchannels.loc[~(ionchannels['symbol'].isna()) & (ionchannels['category'] == "Ionchannel"), ["name", "symbol", "synonyms"]]
ionchannels["synonyms"] = ionchannels["synonyms"].fillna('')
ionchannels = ionchannels.reset_index(drop=True)

CHANNELS  = {}
for _, row in ionchannels.iterrows():
    CHANNELS[row["name"]] = {
        "channel_name": row["name"],
        'akas_to_add_llm': row["symbol"],
        'akas_to_add_pubmed': ', '.join(build_variation(row["name"]) + select_alias(row["synonyms"]))
    }

DRUGS = json.loads(os.getenv("DRUGS", '{"Lidocaine": {"drug_name": "lidocaine", "akas_drug": ""}}'))