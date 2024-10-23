from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from typing import  Optional, List
import json
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate

class Effect(BaseModel):
    analysis: dict = Field(default={}, description="Mandatory analysis of each section and the relevancy related the QUESTION.")
    relevant_sections: List[int] = Field(default=[], description="Relevant and sufficient section ID.")
    sufficient_sections: List[int] = Field(default=[], description="Sufficient section ID that will be used for the next information 'type'.")
    type: Optional[str] = Field(default="NA", description="The overall effect reported between OPEN (enhance, activate, facilitate, agonist), CLOSE (reduce, block, inhibit, antagonist) or NA (not clear effect / not reported / all sections are irrelevant)", examples=["OPEN", "CLOSE", "NA"])
    dose_response: Optional[str] = Field(default="NA", description="All doses/concentrations and corresponding responses/effects if found as well as IC50 or EC50 reported, but ONLY for the specific drug and channel. Return 'NA' (no dose and response found)")

class Study(BaseModel):
    type: Optional[str] = Field(default="UNKNOWN", description="Type of testing reported between: CELL (in lab cell study), ANIMAL (in lab living animal study), HUMAN (clinic study), SILICO (computational study) or UNKNOWN (not enough information)", examples=["CELL", "ANIMAL", "HUMAN", "SILICO", "UNKNOWN"])
    subject: Optional[str] = Field(default="UNKNOWN", description="Cell-line / species / mouse model name / human characteristic, subject to the drug testing")

class DrugMapping(BaseModel):
    effect: Optional[Effect] = Field(default=Effect(), description="Summary of the effect reported, only 'relevant_sections' can be used here.")
    study: Study = Field(default=Study(), description="Summary of the study done in the paper, all sections can be used here.")

DRUG_SCREENING_PARSER = PydanticOutputParser(pydantic_object=DrugMapping)

INSTRUCTION_PROMPT = """Given the following extracted parts of a scientific paper, generate a detailed summary in JSON format related to the effect of particual drug on a specific ion channel.
Only respond when there is strong evidence that the paper reports thorough drug testing, for example discard any information about channel mutants, complex mouse model or high level effect.
For you reasoning and answering keep in mind that some sections may contain syntax error (symbols, math equations, formulas, abbreviations, ponctuation mark etc.)\n{format_instructions}"""

DRUG_SCREENING_QUERY = f"""Does this paper explicitly report an activation effect {{drug_name}} on {{channel_name}}?"""

examples = [
    {
        "question": DRUG_SCREENING_QUERY.format(drug_name="valpiricol", channel_name="Kv2.1 (a.k.a Kcnb1)"),
        "sections": json.dumps({
            "Section 0": "CHO cells treated with valpiricol show a reduction in the kv2.1 potassium current with an IC_50 of 5uM.",
            "Section 1": "Valpiricol at high dose has a strong inhibitory effect on Cav2.1 generated.",
            "Section 2": "Neuro2a cells in culture are treated for 24h with metabol and recorded with manual patch clamp with extracellular solution, revealing an antagonist effect of the drug on kv2.1.",
            "Section 3": "The drug valpiricol at 1ug/ml inactivates by 70% Kcnb1 activity in culture cells."
        }).replace("{", "{{").replace("}", "}}"),
        "answer":  DrugMapping(

            effect = Effect(
                analysis =
                {
                    "Section 0": "Valpiricol reduces/blocks kv2.1 potassium current, so CLOSE effect. (relevant - sufficient)",
                    "Section 1": "Valpiricol blocks Cav2.1, but it does not concern the channel of interest, kv2.1. (irrelevant)",
                    "Section 2": "Kv2.1 is affected by metabol, but it does not concern the drug of interest, valpiricol. (irrelevant)",
                    "Section 3": "Valpiricol inactivates kv2.1 (a.k.a Kcnb1) activity, so CLOSE effect. (relevant - sufficient)"
                },
                relevant_sections = [0, 3],
                sufficient_sections = [0, 3],
                    type="CLOSE",
                    dose_response="5µM -> Ic_50 | 1µg/ml -> 70%"
                ),
            study = Study(
                type="CELL",
                subject="CHO cells"
                )
            ).model_dump_json().replace("{", "{{").replace("}", "}}")
    },
    {
        "question": DRUG_SCREENING_QUERY.format(drug_name="grandolimus (GRD)", channel_name="Cav2.2 (a.k.a Cacna1b)"),
        "sections": json.dumps({
            "Section 0": "GRD is a first-in-class drug that enhances neuronal excitability through the activation of voltage-gated Cav2.2 calcium channels.",
            "Section 1": "Grandolimus is tested in comparison with some other synthetic compound on Cav2.2 kinetic activity. We observed that among all drugs tested, compound CX_109 has the strongest effect on the Cav2.2 activation.",
            "Section 2": "Cav2.2-R234H mutant, that is associated with common cardiac channelopathies, is recorded by automated patch-clamp in MEF cells and present reduce kinetic response when grandolimus is applied on intracellular solution."
        }).replace("{", "{{").replace("}", "}}"),
        "answer":  DrugMapping(
            effect = Effect(
                 analysis =
                    {
                        "Section 0": "Grandolimus activates Cav2.2, so OPEN effect. (relevant - sufficient)",
                        "Section 1": "While CX_109 has an effect on Cav2.2, it is not said for grandolimus. (irrelevant)",
                        "Section 2": "Grandolimus reduced activation of a mutant/modified form of Cav2.2, indicating a CLOSE effect. However mutants shouldn't be taken into consideration and there is no information on normal Cav2.2. (relevant - insufficient)"
                    },
                relevant_sections = [0, 2],
                sufficient_sections = [0],
                type="OPEN"
                ),
            study = Study(
                type="ANIMAL",
                subject="Cav2.2-R234H mutant"
                )
            ).model_dump_json().replace("{", "{{").replace("}", "}}")
    },
    {
        "question": DRUG_SCREENING_QUERY.format(drug_name="myrtigan", channel_name="Nav1.1 (a.k.a Scn1a)"),
        "sections": json.dumps({
            "Section 0": "When all the different drugs were applied on the rat brain slices for 10 minutes, Nav1.1 was blocked by 50%.",
            "Section 1": "Nav1.1-/- KO mice were injected every day for one week with 5mg/kg myrtigan and recorded for NaV current. The knock-out mice showed reduction in sodium current compared with the WT mice after only 2 days of injection.",
            "Section 2": "Epileptic seizures in a model of Nav1.1 related ataxia are reduced upon application of a daily dose of Myrtigan to the water of animals.",
            "Section 3": "In Nav1.1 KO mice, Myrtigan inhibits the synchronous discharges of a network of neurons",
            "Section 4": "Myrtigan inhibited luminozine-induced activation of Scn1a in mammalian cells maintained in 10% humidity and hypoxic conditions.",
            "Section 5": "The M current mediated by the Nav family (Nav1-Nav2) of voltage-gated potassium channels is positively regulated in peripheral sensory nociceptors by physiological concentration of myrtigan.",
            "Section 6": "In patch clamp p8 AAB cell, Myrtigan binding to Nav1.1 subunits is faster than to the other α-subunits. Myrtigan unbinding from the α-subunits is slower than that of carbamazepine and phenytoin."
        }).replace("{", "{{").replace("}", "}}"),
        "answer":  DrugMapping(
            effect = Effect(
                 analysis=
                {
                    "Section 0": "No mention of any specific drug. (irrelevant)",
                    "Section 1": "KO (knock-out) or  -/-  mean that Nav1.1 is absent, so the effect of the drug can't be due to Nav1.1. (relevant - insufficient)",
                    "Section 2": "Myrtigan reduces seizure frequency, that is a disease’s symptom, that is not specific enough to conclude that the effect is directly linked to Nav1.1 channel. (relevant - insufficient)",
                    "Section 3": "Myrtigan inhibits synchronous discharge, that is an overall effect not specific enough to conclude that it is directly linked to Nav1.1 channel. Also it is about Nav1.1 KO model where Nav1.1 is absent. (relevant - insufficient)",
                    "Section 4": "Myrtigan inhibits luminozine activation of Nav1.1 (a.k.a Scn1a), that is an indirect effect of Myrtigan on Nav1.1. (irrelevant)",
                    "Section 5": "While myrtigan has an effect on the Nav family, it is not said specifically for Nav1.1. (irrelevant)",
                    "Section 6": "Faster binding is not enough to conclude the overall activation effect. (relevant - insufficient)"
                },
                relevant_sections = [1, 2, 3, 6],
                sufficient_sections = [],
                dose_response="5mg/kg -> NA"
            ),
            study = Study(
                type="ANIMAL | CELL",
                subject="Nav1.1-/- KO mice | p8 AAB cell"
                )
            ).model_dump_json().replace("{", "{{").replace("}", "}}")
    }
]
DRUG_SCREENING_PROMPT = FewShotPromptTemplate(
    examples=examples,
    example_prompt=PromptTemplate(
        input_variables=["question", "sections", "answer"], template="QUESTION: {question}\n{sections}\n{answer}"
    ),
    prefix=INSTRUCTION_PROMPT,
    suffix="QUESTION: {question}\n{sections}\n",
    input_variables=["question", "sections"],
    partial_variables={
        "format_instructions": DRUG_SCREENING_PARSER.get_format_instructions(),
    },
)

# ----------------Distribution------------------