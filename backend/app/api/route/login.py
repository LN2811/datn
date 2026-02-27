from fastapi import APIRouter, Depends, HTTPException, responses
from sqlmodel import Session
from pydantic import BaseModel, EmailStr