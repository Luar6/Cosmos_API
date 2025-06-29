from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, db, auth
import phonenumbers
from phonenumbers import PhoneNumberFormat
import uuid
from datetime import datetime

cred = credentials.Certificate("credentials.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://if-project-3ded1-default-rtdb.firebaseio.com/"})

ref = db.reference("/")
agenda_ref = ref.child('agenda')

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

@app.get("/testFirebase")
def testar_o_firebase():
    try:
        if ref.get():
            message = "Conectado com successo ao Firebase"
    except Exception as e:
        message = f"Falha ao se conectar com o Firebase: {str(e)}"
    return {"message": message}

@app.get("/getAllUsers/", tags=["Usuários"])
def conseguir_todos_os_usuarios_logado_com_o_email_normal_no_firebase():
    users = []
    page = auth.list_users()
    while page:
        for user in page.users:
            users.append({
                "uid": user.uid,
                "email": user.email or "",
                "passwordHash": user.password_hash or "",
                "passwordSalt": user.password_salt or "",
                "phone_number": user.phone_number or "",
                "display_name": user.display_name or "",
                "photo_url": user.photo_url or "",
            })
        page = page.get_next_page()
    return users

@app.post("/add/user/", tags=["Usuários"])
async def criar_um_usuario_com_email_e_senha(email: str, password: str, display_name: str, phone_number: str | None = None, photo_url: str | None = None):
    user = auth.create_user(
        email=email,
        email_verified=False,
        phone_number=to_e164_br(phone_number),
        password=password,
        display_name=display_name,
        photo_url=photo_url,
        disabled=False)
    message = 'Criado um usuário com sucesso. UID: {0}'.format(user.uid)
    return {"message": message}

@app.delete("/delete/user", tags=["Usuários"])
async def deletar_um_usuario_com_o_uid(uid: str):
    auth.delete_user(uid)
    message = f'O usuário com o UID {uid} foi deletado com sucesso.'
    return {"message": message}

@app.get("/getAllAgendas", tags=["Agenda"])
async def mostrar_todas_as_agendas_criadas():
    if agenda_ref.get() is None:
        message = f'Nenhuma agenda foi criada'
        return {"message": message}
    else:
        return agenda_ref.get()

@app.post("/add/agenda/", tags=["Agenda"])
async def criar_uma_agenda(nome_agenda: str):
    uid = str(uuid.uuid4())
    agenda_ref.update({
        uid: {
            'nome_agenda': nome_agenda
        }
    })
    message = f'A agenda {nome_agenda} com o UID {uid} foi criada com sucesso'
    return {"message": message}

@app.post("/add/agenda/materia", tags=["Agenda"])
async def criar_uma_materia_na_agenda(uid_da_agenda: str, matéria: str):
    matéria_criada = agenda_ref.child(uid_da_agenda).child("matérias")
    uid = str(uuid.uuid4())
    matéria_criada.update({
        uid: {
            'nome_matéria': matéria
        }
    })
    message = f'A matéria {matéria} com o UID {uid} foi criada com sucesso'
    return {"message": message}

@app.post("/add/agenda/tarefa", tags=["Agenda"])
async def criar_uma_tarefa_na_agenda_criada(uid_da_agenda: str, nome_da_tarefa: str, timestamp: str):
    uid = str(uuid.uuid4())
    tarefa_criada = agenda_ref.child(uid_da_agenda).child("tarefas")

    tarefa_criada.update({
        uid: {
            'nome_da_tarefa': nome_da_tarefa,
            'timestamp': timestamp_formatado(timestamp)
        }
    })

    message = f'O tarefa com o UID {uid} foi criada com sucesso.'
    return {"message": message}

@app.post("/add/agenda/evento", tags=["Agenda"])
async def criar_um_evento_na_agenda_criada(uid_da_agenda: str, nome_do_evento: str, timestamp: str):
    uid = str(uuid.uuid4())
    evento_criado = agenda_ref.child(uid_da_agenda).child("evento")

    evento_criado.update({
        uid: {
            'nome_do_evento': nome_do_evento,
            'timestamp': timestamp_formatado(timestamp)
        }
    })

    message = f'O tarefa com o UID {uid} foi criada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/", tags=["Agenda"])
async def deletar_uma_agenda_com_o_uid(uid: str):
    agenda_ref.child(uid).delete()
    message = f'O agenda com o UID {uid} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/materia", tags=["Agenda"])
async def deletar_uma_materia_com_o_uid(uid_da_agenda: str, uid_da_materia: str):
    agenda_ref.child(uid_da_agenda).child("matérias").child(uid_da_materia).delete()
    message = f'A matéria com o UID {uid_da_materia} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/tarefa", tags=["Agenda"])
async def deletar_uma_tarefa_com_o_uid(uid_da_agenda: str, uid_da_tarefa: str):
    agenda_ref.child(uid_da_agenda).child("tarefas").child(uid_da_tarefa).delete()
    message = f'A tarefa com o UID {uid_da_tarefa} foi deletada com sucesso.'
    return {"message": message}

@app.delete("/delete/agenda/evento", tags=["Agenda"])
async def deletar_um_evento_com_o_uid(uid_da_agenda: str, uid_do_evento: str):
    agenda_ref.child(uid_da_agenda).child("evento").child(uid_do_evento).delete()
    message = f'O evento com o UID {uid_do_evento} foi deletado com sucesso.'
    return {"message": message}