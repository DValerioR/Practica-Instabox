"""
Conexión a la base de datos RDS.

Las credenciales NUNCA se guardan en variables de entorno ni hardcodeadas:
se leen desde AWS Secrets Manager en tiempo de ejecución, usando el rol
(instance profile) asignado a la instancia EC2. Solo el NOMBRE del secret
(DB_SECRET_NAME) y la región (AWS_REGION) se configuran como variables de
entorno, porque no son información sensible.

El secret debe tener este formato JSON (es el formato que genera
Secrets Manager al elegir "Credentials for RDS database"):

{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": 5432,
  "dbname": "instabox"
}
"""

import functools
import json
import os

import boto3
import psycopg2

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SECRET_NAME = os.environ["DB_SECRET_NAME"]

_secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)


@functools.lru_cache(maxsize=1)
def _get_db_credentials() -> dict:
    """Obtiene y cachea en memoria (del proceso) las credenciales de RDS."""
    response = _secrets_client.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(response["SecretString"])


def get_connection():
    """Regresa una nueva conexión psycopg2 a la base de datos RDS."""
    creds = _get_db_credentials()
    return psycopg2.connect(
        host=creds["host"],
        port=int(creds.get("port", 5432)),
        dbname=creds.get("dbname", "instabox"),
        user=creds["username"],
        password=creds["password"],
        connect_timeout=5,
    )