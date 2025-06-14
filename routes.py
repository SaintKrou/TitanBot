# routes.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Client, Purchase

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/clients/")
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

@app.post("/clients/")
def create_client(client: Client, db: Session = Depends(get_db)):
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

@app.get("/purchases/")
def list_purchases(db: Session = Depends(get_db)):
    return db.query(Purchase).all()

@app.post("/purchases/")
def create_purchase(purchase: Purchase, db: Session = Depends(get_db)):
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase
