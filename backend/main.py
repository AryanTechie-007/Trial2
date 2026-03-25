import json
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db, Scrape, User
from pydantic import BaseModel
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- AUTH ROUTES ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_pw,
        name=user.name,
        plan_tier="starter" # default plan
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"name": new_user.name, "email": new_user.email}}

@app.post("/api/auth/login")
@limiter.limit("5/minute")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"name": db_user.name, "email": db_user.email}}


# --- COMPETITOR ROUTES ---
class ScrapeRequest(BaseModel):
    url: str
    name: str

@app.post("/api/competitors/scrape")
def trigger_scrape(request: ScrapeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from scraper import scrape_competitor
    from ai_engine import process_competitor_content
    try:
        content, hash_val = scrape_competitor(request.url)
        analysis_dict = process_competitor_content(content)
        
        new_scrape = Scrape(
            user_id=current_user.id,
            competitor_name=request.name.lower(),
            content_hash=hash_val,
            payload=analysis_dict
        )
        db.add(new_scrape)
        db.commit()
        return {"status": "success", "message": f"Successfully scraped and analyzed {request.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/competitors")
def get_competitors(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    scrapes = db.query(Scrape).filter(Scrape.user_id == current_user.id).all()
    unique_names = list(set([s.competitor_name for s in scrapes]))
    return {"competitors": unique_names}

@app.get("/api/competitors/{name}/summary")
def get_competitor_summary(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    scrape = db.query(Scrape).filter(Scrape.user_id == current_user.id, Scrape.competitor_name == name.lower()).order_by(Scrape.timestamp.desc()).first()
    if not scrape:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {"name": scrape.competitor_name, "data": scrape.payload}

class DiscoverRequest(BaseModel):
    company_name: str

class CompareRequest(BaseModel):
    competitors: list[str]

@app.post("/api/competitors/compare")
def compare(request: CompareRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ai_engine import compare_competitors
    try:
        data_list = []
        for name in request.competitors:
            scrape = db.query(Scrape).filter(Scrape.user_id == current_user.id, Scrape.competitor_name == name.lower()).order_by(Scrape.timestamp.desc()).first()
            if scrape and scrape.payload:
                data_list.append({"name": scrape.competitor_name, "payload": scrape.payload})
        
        if len(data_list) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 scraped competitors to compare")
            
        result = compare_competitors(data_list)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/competitors/discover")
def discover(request: DiscoverRequest, current_user: User = Depends(get_current_user)):
    from ai_engine import discover_competitors
    try:
        result = discover_competitors(request.company_name)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ProfileUpdate(BaseModel):
    company_name: str
    plan_tier: str

@app.post("/api/user/profile")
def update_profile(profile: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.company_name = profile.company_name
    current_user.plan_tier = profile.plan_tier
    db.commit()
    return {"status": "success", "user": {"name": current_user.name, "company": current_user.company_name, "plan": current_user.plan_tier}}

@app.get("/api/user/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {"name": current_user.name, "email": current_user.email, "company": current_user.company_name, "plan": current_user.plan_tier}

@app.get("/api/competitors/{name}/strategy")
def get_strategy(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.plan_tier != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise plan required for AI Strike Plans")
        
    if not current_user.company_name:
        raise HTTPException(status_code=400, detail="Please set your baseline company name in your profile first")

    scrape = db.query(Scrape).filter(Scrape.user_id == current_user.id, Scrape.competitor_name == name.lower()).order_by(Scrape.timestamp.desc()).first()
    if not scrape:
        raise HTTPException(status_code=404, detail="Competitor not found")
        
    own_scrape = db.query(Scrape).filter(Scrape.user_id == current_user.id, Scrape.competitor_name == current_user.company_name.lower()).order_by(Scrape.timestamp.desc()).first()

    from ai_engine import generate_strike_plan
    try:
        strike_plan = generate_strike_plan(current_user.company_name, own_scrape.payload if own_scrape else None, name, scrape.payload)
        return {"data": strike_plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
