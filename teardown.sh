#!/bin/bash
# Elimina todos los recursos de AWS creados para la Práctica 1 (InstaBox).
# Requiere el AWS CLI configurado (en el Learner Lab, usa las credenciales
# temporales que te da el laboratorio: aws configure, o exporta
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN).
#
# Uso:
#   1. Edita las variables de la sección CONFIGURA con tus valores reales.
#   2. bash teardown.sh

set -euo pipefail

# ==== CONFIGURA ESTOS VALORES ANTES DE EJECUTAR ====
AWS_REGION="us-east-1"
S3_BUCKET="instabox-fotos-tu-alias"
RDS_INSTANCE_ID="instabox-db"
SECRET_NAME="instabox/rds-credentials"
EC2_INSTANCE_ID="i-xxxxxxxxxxxxxxxxx"
# =====================================================

echo "== Vaciando y eliminando bucket S3: $S3_BUCKET =="
aws s3 rm "s3://$S3_BUCKET" --recursive --region "$AWS_REGION" || true
aws s3api delete-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" || true

echo "== Eliminando instancia RDS: $RDS_INSTANCE_ID =="
aws rds delete-db-instance \
  --db-instance-identifier "$RDS_INSTANCE_ID" \
  --skip-final-snapshot \
  --region "$AWS_REGION" || true

echo "== Eliminando secret de Secrets Manager: $SECRET_NAME =="
aws secretsmanager delete-secret \
  --secret-id "$SECRET_NAME" \
  --force-delete-without-recovery \
  --region "$AWS_REGION" || true

echo "== Terminando instancia EC2: $EC2_INSTANCE_ID =="
aws ec2 terminate-instances \
  --instance-ids "$EC2_INSTANCE_ID" \
  --region "$AWS_REGION" || true

echo ""
echo "Listo. La eliminación de RDS y la terminación de EC2 toman unos minutos;"
echo "confirma en la consola de AWS que los tres recursos quedaron eliminados."