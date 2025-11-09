from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, get_db
from fastapi.staticfiles import StaticFiles
from app import models
from app.schemas import user as schemas
from app.schemas import auth as auth
from app.models.enums import UserRole

from app.api.router import api_router

models.Base.metadata.create_all(bind=engine)
# Initialize the FastAPI app
app = FastAPI(title="Ticketing API", version="0.1.0")

origins = [
        "http://localhost:8080",  # Example: your frontend's local development URL
        "https://your-frontend-domain.com", # Example: your frontend's production URL
        # You can add more origins as needed
    ]

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # Allows all headers
    )
# static files for QR codes & assets
app.mount("/static", StaticFiles(directory="static"), name="static")
# mount versioned routers under /api
app.include_router(api_router, prefix="/api")
# Define the OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@app.post("/register", response_model=schemas.UserRead)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    is_valid = bool(user) and auth.verify_password(form_data.password, user.password)
    # Auto-upgrade plaintext seed passwords to hashed on first successful login
    if user and not is_valid and user.password == form_data.password:
        user.password = auth.get_password_hash(form_data.password)
        db.commit()
        is_valid = True
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    is_admin = (str(user.role) == UserRole.admin.value) or (user.role == UserRole.admin)
    roles = ["admin", "user"] if is_admin else ["user"]
    user_id = user.id
    print(user_id)
    access_token = auth.create_access_token(data={"sub": user.username, "role": roles[0]})
    return {"access_token": access_token, "token_type": "bearer", "isAdmin": is_admin, "roles": roles, "userId": user_id}

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth.verify_token(token)
    print(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
    
@app.get("/users/me", response_model=schemas.UserRead)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user



