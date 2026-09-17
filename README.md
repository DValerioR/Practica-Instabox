# InstaBox — Práctica 1

Backend en Python (FastAPI) para un servicio de fotos estilo Polaroid en eventos.
Un fotógrafo crea un evento, los invitados suben fotos con un mensaje, y al
terminar el evento se descarga un álbum en `.zip` con las polaroids generadas.

## Arquitectura

- **EC2** corre el backend FastAPI, con el instance profile `LabInstanceProfile`
  (no usa las credenciales del usuario).
- **S3** guarda las fotos reducidas (`pictures/`) y las polaroids compuestas
  (`polaroids/`), cada una con nombre único (UUID).
- **RDS (PostgreSQL)** guarda dos tablas: `events` y `photos`, relacionadas por
  `event_id`.
- **Secrets Manager** guarda usuario/contraseña/host de RDS; la app los lee en
  tiempo de ejecución con boto3, nunca están en variables de entorno ni en el
  código.

```
Invitado --foto+mensaje--> EC2 (FastAPI) --credenciales--> Secrets Manager
                                |                              |
                                v                              v
                               S3  <---- rutas guardadas ---- RDS (events, photos)
```

## Estructura del repositorio

```
instabox/
├── app/
│   ├── main.py        # endpoints FastAPI
│   ├── db.py           # conexión a RDS vía Secrets Manager
│   ├── s3_utils.py      # subir/bajar objetos de S3
│   └── polaroid.py      # resize 128x128 + composición Polaroid
├── deploy/
│   ├── schema.sql        # creación de tablas events/photos
│   ├── ec2-setup.sh       # bootstrap de la instancia EC2
│   └── instabox.service    # unidad systemd para correr la app
├── requirements.txt
├── .env.example
├── teardown.sh
└── README.md
```

## 1. Crear el bucket S3

```bash
aws s3api create-bucket --bucket instabox-fotos-tu-alias --region us-east-1
```

Usa un nombre de bucket único (por ejemplo con tu usuario o alias). No hace
falta hacerlo público: la app sube y descarga los objetos con el instance
profile de la EC2.

## 2. Crear la base de datos en RDS

En la consola de AWS (o CLI): RDS → Create database → PostgreSQL → plantilla
"Free tier" → identificador `instabox-db` → usuario y contraseña maestros →
en "Connectivity" pon la instancia en la misma VPC donde vas a crear la EC2 y
crea/usa un security group que permita el puerto 5432 solo desde el security
group de la EC2 (no la hagas públicamente accesible).

Anota el **endpoint** que te da RDS al terminar de crearse; lo necesitas para
el secret del paso 3.

Una vez que la instancia esté disponible, conéctate y crea las tablas:

```bash
psql -h <endpoint-rds> -U <usuario_maestro> -d postgres -c "CREATE DATABASE instabox;"
psql -h <endpoint-rds> -U <usuario_maestro> -d instabox -f deploy/schema.sql
```

(Puedes correr esto desde tu máquina si el security group te permite el
acceso temporalmente, o desde la propia EC2 una vez creada, ya que instalamos
`postgresql-client` en el bootstrap.)

## 3. Guardar las credenciales en Secrets Manager

```bash
aws secretsmanager create-secret \
  --name instabox/rds-credentials \
  --secret-string '{
    "username": "<usuario_maestro>",
    "password": "<password>",
    "host": "<endpoint-rds>",
    "port": 5432,
    "dbname": "instabox"
  }'
```

Este es el único lugar donde vive la contraseña de la base de datos.

## 4. Lanzar la instancia EC2

- AMI: Ubuntu Server 22.04 o 24.04.
- Tipo: `t3.micro` (suficiente para la práctica).
- **IAM instance profile: `LabInstanceProfile`** (ya trae permisos para S3,
  RDS y Secrets Manager en el Learner Lab).
- Security group: permite entrada TCP 8000 (o 80 si prefieres mapear el
  puerto) desde tu IP o `0.0.0.0/0` para poder probarlo, y SSH (22) desde tu
  IP.
- Debe estar en la misma VPC/subred que puede alcanzar el security group de
  RDS.

Conéctate por SSH y copia el proyecto (por ejemplo con `git clone` de tu
repositorio, o `scp` si prefieres):

```bash
git clone <url-de-tu-repo> /opt/instabox
cd /opt/instabox
cp .env.example .env.runtime
nano .env.runtime   # pon tu AWS_REGION, DB_SECRET_NAME y S3_BUCKET reales
sudo bash deploy/ec2-setup.sh
```

El script instala dependencias, crea un virtualenv, instala
`requirements.txt` y registra `instabox` como servicio systemd, ya escuchando
en el puerto 8000.

Verifica:

```bash
curl http://localhost:8000/
systemctl status instabox
journalctl -u instabox -f
```

## 5. Probar los endpoints

Sustituye `<EC2_IP>` por la IP pública de tu instancia.

**Crear un evento:**

```bash
curl -X POST http://<EC2_IP>:8000/events \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Ana y Luis", "event_type": "boda", "event_date": "2026-09-20"}'
# -> {"event_id": "..."}
```

**Subir una foto:**

```bash
curl -X POST http://<EC2_IP>:8000/upload \
  -F "event_id=<event_id>" \
  -F "message=¡Felicidades!" \
  -F "photo=@foto1.jpg"
```

**Consultar el evento:**

```bash
curl http://<EC2_IP>:8000/events/<event_id>
# -> {"event_id": "...", "client_name": "...", "photo_count": 3, ...}
```

**Cerrar el evento y descargar el álbum:**

```bash
curl -X POST http://<EC2_IP>:8000/finish \
  -H "Content-Type: application/json" \
  -d '{"event_id": "<event_id>"}' \
  -o album.zip
```

También puedes importar estas mismas llamadas en Postman (JSON para
`/events` y `/finish`, `form-data` para `/upload` con el campo `photo` como
tipo "File").

## 6. Eliminar los recursos (teardown)

Edita las variables al inicio de `teardown.sh` con los identificadores reales
(nombre del bucket, id de la instancia RDS, nombre del secret, id de la
instancia EC2) y ejecútalo:

```bash
bash teardown.sh
```

Esto vacía y borra el bucket S3, elimina la instancia RDS (sin snapshot
final), borra el secret de Secrets Manager y termina la instancia EC2.
Confirma en la consola de AWS que los tres recursos ya no existen.

## Declaración de uso de IA

Recuerda incluir en tu reporte PDF una declaración honesta de qué partes
generaste con ayuda de IA (por ejemplo: estructura del backend, scripts de
despliegue) y qué revisaste o ajustaste tú mismo, como pide el enunciado de
la práctica.