import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, Cookie,UploadFile,File
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "postgresql://admin:asdfgh@127.0.0:5432/db_user_auth"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
#ORM
class User(Base):
    __tablename__ = "tbl_users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    phone = Column(String, unique=True, index=True)
    
    profile = relationship("Profile", back_populates="user")

class Profile(Base):
    __tablename__ = "tbl_profiles"
    id = Column(Integer, primary_key=True, index=True)
    profile_picture = Column(String)
    user_id = Column(Integer, ForeignKey("tbl_users.id"))
    
    user = relationship("User", back_populates="profile")
#encoded the password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str
    profile_picture: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    profile_picture: str

@app.get("/register/", response_class=HTMLResponse)
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/user_registeration/")
async def register_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    profile_picture: UploadFile = File(...),
    response: HTMLResponse = None
):
    db = SessionLocal()
    
    # Check if email or phone already exist
    user_exists = db.query(User).filter(
        (User.email == email) | (User.phone == phone)
    ).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email or phone already registered")
    
    # Hash the user's password before storing it in the database
    hashed_password = pwd_context.hash(password)
    
    # Create a new user
    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed_password,
        phone=phone
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    #storing the user data in tbl_user and profile in tbl_profile
    if profile_picture:
        new_profile = Profile(profile_picture=profile_picture.filename, user_id=new_user.id)
        db.add(new_profile)
        db.commit()
    db.close()
    if response is not None:
        response.headers["Location"] = "/home/"
        response.status_code = 302 
    return {"message": "Login successful"}

@app.get("/", response_class=HTMLResponse)
async def read_login(request: Request, username: str = Cookie(None),error_message:str = None):
    print(error_message)
    return templates.TemplateResponse("login.html", {"request": request, "username": username,'errormsg':error_message})

@app.post("/")
async def login_user(request:Request,
                         username: str = Form(...),
                          password: str = Form(...),
                           response: HTMLResponse = None):
    db = SessionLocal()
    user = db.query(User).filter(User.email == username).first()
    
    if user is None or not pwd_context.verify(password, user.password_hash):
        error_message = "Invalid username or password. Please try again."
        return await read_login(request=request, username=username, error_message=error_message)
    
    if response is not None:
        response.set_cookie(key="username", value=username)
        response.headers["Location"] = "/home/"
        response.status_code = 302 
    
    return {"message": "Login successful"}


@app.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    db = SessionLocal()
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.close()
    return user

# Home page to display all registered users
@app.get("/home/", response_class=HTMLResponse)
async def read_home(request: Request):
    db = SessionLocal()
    users_with_profiles = db.query(User, Profile).join(User.profile)
    
    user_data = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "profile_picture": profile.profile_picture
        }
        for user, profile in users_with_profiles
    ]
    print(user_data)
    db.close()
    return templates.TemplateResponse("home.html", {"request": request, "users": user_data})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000)