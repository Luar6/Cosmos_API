from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
import firebase_admin
from firebase_admin import credentials, db, auth
import phonenumbers
from phonenumbers import PhoneNumberFormat
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
import random
import string

load_dotenv()

cred_info = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL")
}

cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred, {"databaseURL": os.getenv("DATABASE_URL")})

ref = db.reference("/")
agenda_ref = ref.child('agendas')

def to_e164_br(phone_number):
    try:
        parsed = phonenumbers.parse(phone_number, "BR")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        else:
            return None
    except phonenumbers.NumberParseException:
        return None

def timestamp_formatado(timestamp):
    try:
        data = datetime.fromisoformat(timestamp)
        timestamp_formatado = data.isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de timestamp inválido. Use ISO 8601 (ex: '2025-06-27T14:00:00')")

def check_uid_exists(uid: str):
    try:
        user = auth.get_user(uid)
        print(f"✅ User exists: {user.uid}, email: {user.email}")
        return True
    except auth.UserNotFoundError:
        print("❌ No user found with that UID.")
        return False
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return False

def generate_random_invite_url(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(chars, k=length))

STANDARD_RESPONSES = {
    400: {"description": "Bad Request"},
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
    404: {"description": "Not Found"},
    500: {"description": "Internal Server Error"},
}

tags_metadata = [
    {
        "name": "Usuários",
        "description": "Operações com os usuários",
    },
    {
        "name": "Agenda",
        "description": "Operações com a agenda",
    },
]

app = FastAPI(openapi_tags=tags_metadata)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/testFirebase", responses=STANDARD_RESPONSES)
def testar_o_firebase():
    try:
        if ref.get():
            message = "Conectado com successo ao Firebase"
            return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao se conectar com o Firebase: {str(e)}")

from fastapi import APIRouter

@app.get("/invite/{uid_da_agenda}", responses=STANDARD_RESPONSES)
def mandar_um_convite_para_entrar_na_turma_tipo_o_whatsapp(uid_da_agenda: str, request: Request):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()

    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    # Detecta o dispositivo
    user_agent = request.headers.get("user-agent", "").lower()

    # Deep link do seu app (Expo deve estar configurado com "scheme": "cosmos")
    deep_link_url = "cosmos://home"

    # URL da Play Store (o pacote deve bater com o app.json do Expo)
    play_store_url = "https://play.google.com/store/apps/details?id=com.seuapp.android"

    if "android" in user_agent:
        intent_url = (
            f"intent://home#Intent;"
            f"scheme=cosmos;"
            f"package=com.seuapp.android;"
            f"end"
        )
        return RedirectResponse(intent_url)

    elif "iphone" in user_agent or "ipad" in user_agent:
        return RedirectResponse(deep_link_url)

    # Fallback para outros dispositivos (desktop, etc)
    return RedirectResponse(play_store_url)

@app.get("/getAllUsers/", tags=["Usuários"], responses=STANDARD_RESPONSES)
def conseguir_todos_os_usuarios_logado_com_o_email_normal_no_firebase():
    users = []
    page = auth.list_users()
    while page:
        for user in page.users:
            users.append({
                "uid": user.uid,
                "email": user.email,
                "passwordHash": user.password_hash,
                "passwordSalt": user.password_salt,
                "display_name": user.display_name,
                "phone_number": user.phone_number or "",
                "invite_url": user.invite_url,
                "photo_url": user.photo_url or "",
            })
        page = page.get_next_page()
    return users

@app.post("/add/user/", tags=["Usuários"], responses=STANDARD_RESPONSES)
async def criar_um_usuario_com_email_e_senha(email: str, password: str, display_name: str, phone_number: str | None = None, photo_url: str | None = None):
    user = auth.create_user(
        email=email,
        email_verified=False,
        phone_number=to_e164_br(phone_number),
        password=password,
        display_name=display_name,
        photo_url=photo_url,
        invite_url=generate_random_invite_url(),
        disabled=False)
    message = 'Criado um usuário com sucesso. UID: {0}'.format(user.uid)
    return {"message": message}

@app.delete("/delete/user", tags=["Usuários"], responses=STANDARD_RESPONSES)
async def deletar_um_usuario_com_o_uid(uid: str):
    if check_uid_exists(uid):
        auth.delete_user(uid)
        message = f'O usuário com o UID {uid} foi deletado com sucesso.'
        return {"message": message}
    else:
        raise HTTPException(status_code=400, detail="Este usuário não existe no banco de dados")

@app.get("/getAllAgendas", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def mostrar_todas_as_agendas_criadas():
    if agenda_ref.get() is None:
        message = f'Nenhuma agenda foi criada'
        return {"message": message}
    else:
        return agenda_ref.get()

@app.post("/add/agenda/", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def criar_uma_agenda(nome_agenda: str, uid_do_responsavel: str):
    if check_uid_exists(uid_do_responsavel):
        uid = str(uuid.uuid4())
        agenda_ref.update({
            uid: {
                'nome_agenda': nome_agenda,
                'uid_do_responsável': uid_do_responsavel
            }
        })
        message = f'A agenda {nome_agenda} com o UID {uid} foi criada com sucesso'
        return {"message": message}
    else:
        raise HTTPException(status_code=401, detail="Este usuário não existe no banco de dados")

@app.post("/add/agenda/membro", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def adicionar_um_membro_na_agenda_já_criada(uid_da_agenda: str, uid_do_membro: str):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()
    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    if not check_uid_exists(uid_do_membro):
        raise HTTPException(status_code=400, detail="Este usuário não existe no banco de dados")

    user = auth.get_user(uid_do_membro)

    membro_ref = agenda_node.child("membros")
    membro_ref.update({
        user.uid: {
            'nome_do_usuário': user.display_name
        }
    })
    message = f'O membro {user.display} com o UID {user.uid} foi adicionado com sucesso'
    return {"message": message}

@app.post("/add/agenda/materia", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def criar_uma_materia_na_agenda_já_criada(uid_da_agenda: str, nome_da_matéria: str, nome_do_professor: str | None = None, horario_de_inicio_da_materia: str | None = None, horario_de_fim_da_materia: str | None = None):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()
    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    matérias_ref = agenda_node.child("matérias")
    uid = str(uuid.uuid4())
    matérias_ref.update({
        uid: {
            'nome_matéria': nome_da_matéria,
            'professor': nome_do_professor,
            'horario_de_início': horario_de_inicio_da_materia,
            "horário_de_fim": horario_de_fim_da_materia
        }
    })
    message = f'A matéria {nome_da_matéria} com o UID {uid} foi criada com sucesso'
    return {"message": message}

@app.post("/add/agenda/tarefa", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def criar_uma_tarefa_na_agenda_já_criada(uid_da_agenda: str, nome_da_tarefa: str, timestamp: str):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()
    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    uid = str(uuid.uuid4())
    tarefa_criada = agenda_node.child("tarefas")
    tarefa_criada.update({
        uid: {
            'nome_da_tarefa': nome_da_tarefa,
            'timestamp': timestamp_formatado(timestamp)
        }
    })
    message = f'A tarefa com o UID {uid} foi criada com sucesso.'
    return {"message": message}

@app.post("/add/agenda/evento", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def criar_um_evento_na_agenda_já_criada(uid_da_agenda: str, nome_do_evento: str, timestamp: str):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()
    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    uid = str(uuid.uuid4())
    evento_criado = agenda_node.child("eventos")
    evento_criado.update({
        uid: {
            'nome_do_evento': nome_do_evento,
            'timestamp': timestamp_formatado(timestamp)
        }
    })
    message = f'O evento com o UID {uid} foi criado com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def deletar_uma_agenda_com_o_uid(uid_da_agenda: str):
    agenda_node = agenda_ref.child(uid_da_agenda)
    agenda_data = agenda_node.get()
    if not agenda_data:
        raise HTTPException(status_code=404, detail=f"A agenda com o UID {uid_da_agenda} não existe")

    agenda_node.delete()
    message = f'A agenda com o UID {uid_da_agenda} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/materia", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def deletar_uma_materia_com_o_uid(uid_da_agenda: str, uid_da_materia: str):
    matéria_node = agenda_ref.child(uid_da_agenda).child("matérias").child(uid_da_materia)
    matéria_data = matéria_node.get()
    if not matéria_data:
        raise HTTPException(status_code=404, detail=f"A matéria com o UID {uid_da_materia} na agenda {uid_da_agenda} não existe")

    matéria_node.delete()
    message = f'A matéria com o UID {uid_da_materia} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/tarefa", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def deletar_uma_tarefa_com_o_uid(uid_da_agenda: str, uid_da_tarefa: str):
    tarefa_node = agenda_ref.child(uid_da_agenda).child("tarefas").child(uid_da_tarefa)
    tarefa_data = tarefa_node.get()
    if not tarefa_data:
        raise HTTPException(status_code=404, detail=f"A tarefa com o UID {uid_da_tarefa} na agenda {uid_da_agenda} não existe")

    tarefa_node.delete()
    message = f'A tarefa com o UID {uid_da_tarefa} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/evento", tags=["Agenda"], responses=STANDARD_RESPONSES)
async def deletar_um_evento_com_o_uid(uid_da_agenda: str, uid_do_evento: str):
    evento_node = agenda_ref.child(uid_da_agenda).child("eventos").child(uid_do_evento)
    evento_data = evento_node.get()
    if not evento_data:
        raise HTTPException(status_code=404, detail=f"O evento com o UID {uid_do_evento} na agenda {uid_da_agenda} não existe")

    evento_node.delete()
    message = f'O evento com o UID {uid_do_evento} foi deletado com sucesso.'
    return {"message": message}