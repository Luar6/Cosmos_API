from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, db, auth
import phonenumbers
from phonenumbers import PhoneNumberFormat

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
            return None  # Invalid number
    except phonenumbers.NumberParseException:
        return None  # Failed to parse

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/testFirebase")
def try_Firebase():
    print(ref.get())

@app.get("/getAllUsers/")
def get_all_users_logged_on_firebase_email():
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

@app.post("/add/user/")
async def create_user_with_normal_email_and_password(email: str, password: str, phone_number: str | None = None, display_name: str | None = None, photo_url: str | None = None):
    user = auth.create_user(
        email=email,
        email_verified=False,
        phone_number=to_e164_br(phone_number),
        password=password,
        display_name=display_name,
        photo_url=photo_url,
        disabled=False)
    message = 'Sucessfully created new user: {0}'.format(user.uid)
    return {"message": message}

@app.post("/add/agenda/")
async def create_agenda(nome_agenda: str, matéria: str):
    agenda_ref.set({
        nome_agenda: {
            'matéria': matéria
        }
    })