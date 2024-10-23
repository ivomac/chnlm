### Description

In this folder, there is scripts for_
- channelAID: A retrival-augmented generation (RAG) tool for our custom data.
- drug_screening: A drug screening based on literature data using channelAID tool.
- channelpedia_writer: A wiki-like section writer for channelpedia using channelAID tool.

### How to run

First you need a elasticsearch database instance (either locally on somewhere on a cluster). Use the database scripts to fill it.
Since chanelAID is as service (bbs-pipeline from ML-team) it is not part of the code here but the service can point to that database.
AI-drug screening will use that database and directly fill the sql database of channelpedia, so you need the credential of both.