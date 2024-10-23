import os
import json
from typing import Optional
import mysql.connector
from mysql.connector.connection import MySQLConnection

TABLE_NAME = "drug_mappings"

def get_sql_client() -> Optional[MySQLConnection]:
    """Get the Elasticsearch client."""
    sql_client = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
        )
    return sql_client


def remove_main_table():
    try:
        create_books_table = f"DROP TABLE {TABLE_NAME}"
        # Create cursor object
        client = get_sql_client()
        with client.cursor() as cursor:
            cursor.execute(create_books_table)
    except Exception as e:
        print(e)

def create_main_table():
    try:
        create_books_table = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            drug VARCHAR(30),
            channel VARCHAR(30),
            family VARCHAR(50),
            pubmed_id INT,
            format VARCHAR(30),
            output JSON,
            metadata JSON
        )
        """
        # Create cursor object
        client = get_sql_client()
        with client.cursor() as cursor:
            cursor.execute(create_books_table)
    except Exception as e:
        print(e)

def record_exist(drug, channel, pubmed_id):
    client = get_sql_client()
    sql_command = f"""SELECT id, output, format
    FROM {TABLE_NAME}
    WHERE drug='{drug}' AND
        channel='{channel}' AND
        pubmed_id='{pubmed_id}';"""
    with client.cursor() as cursor:
        cursor.execute(sql_command)
        results = cursor.fetchall()
        client.commit()
    if len(results) > 0:
        return results[0][0], json.loads(results[0][1]), results[0][2]
    return None, None, None


def add_row(record_id, values):
    if record_id is None:
        sql_command = f"""INSERT INTO {TABLE_NAME}
        (drug, channel, family, pubmed_id, format, output, metadata)
        VALUES ('{values["drug"]}', '{values["channel"]}', '{values["family"]}', '{values["pubmed_id"]}', %s, %s, %s)"""
    else:
        sql_command = f"""UPDATE {TABLE_NAME} 
        SET format = %s,
        output = %s,
        metadata = %s     WHERE id = {record_id}
        """
    client = get_sql_client()
    with client.cursor() as cursor:
        cursor.execute(sql_command,
                    (
                        values["format"],
                        json.dumps(values["output"]),
                        json.dumps(values["metadata"])
                    )
                )
        client.commit()
    
        


