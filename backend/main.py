from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Boolean, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union, Literal
import shopify
import openai
import os
import json
import pandas as pd
import numpy as np
import datetime as dt
from typing import List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import pyotp
import uuid
import requests
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import aiohttp
import asyncio
import io
import xlsxwriter
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
import logging
import stripe
import bs4
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from cachetools import TTLCache, cached

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="AI E-Commerce Manager",
    description="Complete e-commerce management platform with AI-powered optimization",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ecom_ai_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# API Keys and Configurations
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "your_shopify_api_key")
SHOPIFY_SECRET = os.getenv("SHOPIFY_SECRET", "your_shopify_secret")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
SECRET_KEY = os.getenv("SECRET_KEY", "your_jwt_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "your_stripe_api_key")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "your_sendgrid_api_key")

# Set API keys for external services
openai.api_key = OPENAI_API_KEY
stripe.api_key = STRIPE_API_KEY

# Initialize NLP tools
try:
    nltk.download('vader_lexicon', quiet=True)
    sia = SentimentIntensityAnalyzer()
except Exception as e:
    logger.error(f"Error initializing NLP tools: {e}")
    sia = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 with Password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# In-memory cache for frequent operations
cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes TTL

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    preferences = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    avatar_url = Column(String, nullable=True)
    subscription_tier = Column(String, default="free")
    businesses = relationship("Business", back_populates="owner")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role = relationship("Role", back_populates="users")
    achievements = relationship("UserAchievement", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(JSON)
    users = relationship("User", back_populates="role")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    achieved_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="users")

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    points = Column(Integer, default=0)
    badge_url = Column(String, nullable=True)
    users = relationship("UserAchievement", back_populates="achievement")

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform_type = Column(String)  # Shopify, Affiliate, BigCommerce, Magento, Etsy, etc.
    name = Column(String)
    platform_url = Column(String)
    platform_token = Column(String)
    platform_details = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSON, default=lambda: {})
    owner = relationship("User", back_populates="businesses")
    dashboards = relationship("Dashboard", back_populates="business")
    ab_tests = relationship("ABTest", back_populates="business")

class Dashboard(Base):
    __tablename__ = "dashboards"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String)
    layout = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_default = Column(Boolean, default=False)
    business = relationship("Business", back_populates="dashboards")
    widgets = relationship("Widget", back_populates="dashboard")

class Widget(Base):
    __tablename__ = "widgets"
    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"))
    widget_type = Column(String)  # chart, table, metric, etc.
    title = Column(String)
    settings = Column(JSON, default=lambda: {})
    position = Column(JSON, default=lambda: {"x": 0, "y": 0, "w": 3, "h": 2})
    dashboard = relationship("Dashboard", back_populates="widgets")

class ABTest(Base):
    __tablename__ = "ab_tests"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String)
    description = Column(String, nullable=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)
    status = Column(String, default="draft")  # draft, active, completed, cancelled
    test_type = Column(String)  # product_listing, price, description, etc.
    variants = Column(JSON)
    results = Column(JSON, nullable=True)
    winner_variant = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    business = relationship("Business", back_populates="ab_tests")

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    feedback_type = Column(String)  # suggestion, bug, general, etc.
    status = Column(String, default="pending")  # pending, reviewed, implemented, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="feedback")

# Pydantic models for request validation
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    expires_at: datetime
    user_id: int
    username: str
    is_superuser: bool

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    is_superuser: Optional[bool] = False

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    avatar_url: Optional[str]
    subscription_tier: str
    preferences: Dict[str, Any]
    
    class Config:
        orm_mode = True

class MFASetup(BaseModel):
    enable: bool
    token: Optional[str] = None

class BusinessCreate(BaseModel):
    platform_type: str
    name: str
    platform_url: str
    platform_token: str
    platform_details: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    platform_url: Optional[str] = None
    platform_token: Optional[str] = None
    platform_details: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class BusinessOut(BaseModel):
    id: int
    name: str
    platform_type: str
    platform_url: str
    platform_details: Dict[str, Any]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class OptimizationRequest(BaseModel):
    business_id: int
    optimization_type: str  # "categories", "pricing", "seo", etc.
    parameters: Optional[Dict[str, Any]] = None

class PredictionRequest(BaseModel):
    business_id: int
    prediction_type: str  # "sales", "inventory", "customer_behavior", etc.
    timeframe: Optional[str] = "30d"  # 7d, 30d, 90d, etc.
    parameters: Optional[Dict[str, Any]] = None

class SentimentAnalysisRequest(BaseModel):
    business_id: int
    text_data: Optional[List[str]] = None
    product_ids: Optional[List[str]] = None
    source: Optional[str] = None  # "reviews", "social_media", "custom", etc.

class DashboardCreate(BaseModel):
    business_id: int
    name: str
    layout: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = False

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None

class WidgetCreate(BaseModel):
    dashboard_id: int
    widget_type: str
    title: str
    settings: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None

class WidgetUpdate(BaseModel):
    title: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None

class ABTestCreate(BaseModel):
    business_id: int
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    test_type: str
    variants: Dict[str, Any]

class ABTestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    variants: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    winner_variant: Optional[str] = None

class FeedbackCreate(BaseModel):
    content: str
    feedback_type: str

class FeedbackUpdate(BaseModel):
    content: Optional[str] = None
    feedback_type: Optional[str] = None
    status: Optional[str] = None

class ReportRequest(BaseModel):
    business_id: int
    report_type: str  # "sales", "inventory", "customers", "marketing", etc.
    start_date: datetime
    end_date: datetime
    format: str = "pdf"  # pdf, xlsx, csv
    parameters: Optional[Dict[str, Any]] = None

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication and security functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        is_superuser: bool = payload.get("is_superuser", False)
        if username is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id, is_superuser=is_superuser)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

def generate_mfa_secret():
    return pyotp.random_base32()

def verify_mfa_token(user: User, token: str):
    if not user.mfa_secret:
        return False
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.verify(token)

# Helper functions for specific platforms
def connect_to_platform(business: Business):
    """Helper function to connect to various e-commerce platforms"""
    if business.platform_type.lower() == "shopify":
        return connect_to_shopify(business.platform_url, business.platform_token)
    elif business.platform_type.lower() == "bigcommerce":
        return connect_to_bigcommerce(business.platform_url, business.platform_token)
    elif business.platform_type.lower() == "magento":
        return connect_to_magento(business.platform_url, business.platform_token)
    elif business.platform_type.lower() == "etsy":
        return connect_to_etsy(business.platform_url, business.platform_token)
    elif business.platform_type.lower() == "woocommerce":
        return connect_to_woocommerce(business.platform_url, business.platform_token)
    else:
        raise ValueError(f"Platform {business.platform_type} not supported")

def connect_to_shopify(platform_url, platform_token):
    """Helper function to connect to Shopify API"""
    session = shopify.Session(platform_url, "2023-10", platform_token)
    shopify.ShopifyResource.activate_session(session)
    return session

def connect_to_bigcommerce(platform_url, platform_token):
    """Helper function to connect to BigCommerce API"""
    # Implementation for BigCommerce connection
    return {"url": platform_url, "token": platform_token}

def connect_to_magento(platform_url, platform_token):
    """Helper function to connect to Magento API"""
    # Implementation for Magento connection
    return {"url": platform_url, "token": platform_token}

def connect_to_etsy(platform_url, platform_token):
    """Helper function to connect to Etsy API"""
    # Implementation for Etsy connection
    return {"url": platform_url, "token": platform_token}

def connect_to_woocommerce(platform_url, platform_token):
    """Helper function to connect to WooCommerce API"""
    # Implementation for WooCommerce connection
    return {"url": platform_url, "token": platform_token}

# Gamification functions
def check_achievements(user_id: int, db: Session):
    """Check and award achievements based on user activity"""
    # Example: Award achievement for connecting first business
    user = db.query(User).filter(User.id == user_id).first()
    businesses_count = db.query(Business).filter(Business.user_id == user_id).count()
    
    # First business achievement
    if businesses_count == 1:
        first_business_achievement = db.query(Achievement).filter(Achievement.name == "First Business").first()
        if first_business_achievement and not db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == first_business_achievement.id
        ).first():
            new_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=first_business_achievement.id
            )
            db.add(new_achievement)
            db.commit()
            return {"achievement": first_business_achievement.name, "points": first_business_achievement.points}
    
    # Multiple businesses achievement
    if businesses_count >= 3:
        multiple_business_achievement = db.query(Achievement).filter(Achievement.name == "Business Expert").first()
        if multiple_business_achievement and not db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == multiple_business_achievement.id
        ).first():
            new_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=multiple_business_achievement.id
            )
            db.add(new_achievement)
            db.commit()
            return {"achievement": multiple_business_achievement.name, "points": multiple_business_achievement.points}
    
    return None

# ML Prediction Functions
def predict_sales(business_id: int, timeframe: str, parameters: Dict[str, Any], db: Session):
    """Predict sales for a business using machine learning"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Connect to the platform and get historical sales data
    try:
        # This is a simplified example - in a real app, you'd fetch and process actual sales data
        # For demo purposes, we'll create synthetic data
        
        # Create synthetic sales data for the past 90 days
        today = datetime.now()
        date_range = [today - timedelta(days=i) for i in range(90)]
        
        # Generate random sales with a trend and some seasonality
        np.random.seed(42)  # For reproducible results
        base_sales = 1000
        trend = np.linspace(0, 300, 90)  # Upward trend
        seasonality = 200 * np.sin(np.linspace(0, 6*np.pi, 90))  # Weekly seasonality
        noise = np.random.normal(0, 100, 90)  # Random noise
        
        sales = base_sales + trend + seasonality + noise
        sales = np.maximum(sales, 0)  # Ensure no negative sales
        
        # Create DataFrame for modeling
        df = pd.DataFrame({
            'date': date_range,
            'sales': sales,
            'day_of_week': [d.weekday() for d in date_range],
            'day_of_month': [d.day for d in date_range],
            'month': [d.month for d in date_range]
        })
        
        # Feature engineering
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Define features and target
        features = ['day_sin', 'day_cos', 'month_sin', 'month_cos', 'day_of_month']
        X = df[features]
        y = df['sales']
        
        # Train a Random Forest model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Generate future dates for prediction
        if timeframe == '7d':
            future_days = 7
        elif timeframe == '30d':
            future_days = 30
        elif timeframe == '90d':
            future_days = 90
        else:
            future_days = 30  # Default
        
        future_dates = [today + timedelta(days=i) for i in range(1, future_days + 1)]
        future_df = pd.DataFrame({
            'date': future_dates,
            'day_of_week': [d.weekday() for d in future_dates],
            'day_of_month': [d.day for d in future_dates],
            'month': [d.month for d in future_dates]
        })
        
        future_df['day_sin'] = np.sin(2 * np.pi * future_df['day_of_week'] / 7)
        future_df['day_cos'] = np.cos(2 * np.pi * future_df['day_of_week'] / 7)
        future_df['month_sin'] = np.sin(2 * np.pi * future_df['month'] / 12)
        future_df['month_cos'] = np.cos(2 * np.pi * future_df['month'] / 12)
        
        # Make predictions
        future_df['predicted_sales'] = model.predict(future_df[features])
        
        # Calculate confidence intervals (simplified)
        forecast_stddev = df['sales'].std() * 0.2  # Simplification
        future_df['lower_bound'] = future_df['predicted_sales'] - 1.96 * forecast_stddev
        future_df['upper_bound'] = future_df['predicted_sales'] + 1.96 * forecast_stddev
        
        # Format results
        forecast = [{
            'date': row['date'].strftime('%Y-%m-%d'),
            'predicted_sales': float(row['predicted_sales']),
            'lower_bound': float(max(0, row['lower_bound'])),  # No negative sales
            'upper_bound': float(row['upper_bound'])
        } for _, row in future_df.iterrows()]
        
        # Calculate aggregate statistics
        total_predicted = future_df['predicted_sales'].sum()
        avg_predicted = future_df['predicted_sales'].mean()
        min_predicted = future_df['predicted_sales'].min()
        max_predicted = future_df['predicted_sales'].max()
        
        return {
            'forecast': forecast,
            'summary': {
                'total_predicted_sales': float(total_predicted),
                'average_daily_sales': float(avg_predicted),
                'minimum_daily_sales': float(min_predicted),
                'maximum_daily_sales': float(max_predicted),
                'timeframe': f"{future_days} days"
            }
        }
        
    except Exception as e:
        logger.error(f"Error predicting sales: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error predicting sales: {str(e)}")

def analyze_sentiment(texts: List[str]):
    """Analyze sentiment of customer reviews or social media posts"""
    if not sia:
        raise HTTPException(status_code=500, detail="Sentiment analysis tools not available")
    
    results = []
    for text in texts:
        sentiment = sia.polarity_scores(text)
        # Classify the sentiment based on compound score
        if sentiment['compound'] >= 0.05:
            sentiment_label = "positive"
        elif sentiment['compound'] <= -0.05:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"
        
        results.append({
            'text': text,
            'sentiment': sentiment_label,
            'scores': {
                'positive': sentiment['pos'],
                'negative': sentiment['neg'],
                'neutral': sentiment['neu'],
                'compound': sentiment['compound']
            }
        })
    
    # Calculate aggregate sentiment statistics
    total_texts = len(results)
    positive_count = sum(1 for r in results if r['sentiment'] == 'positive')
    negative_count = sum(1 for r in results if r['sentiment'] == 'negative')
    neutral_count = sum(1 for r in results if r['sentiment'] == 'neutral')
    avg_compound = sum(r['scores']['compound'] for r in results) / total_texts if total_texts > 0 else 0
    
    return {
        'results': results,
        'summary': {
            'total_texts': total_texts,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_percentage': (positive_count / total_texts * 100) if total_texts > 0 else 0,
            'negative_percentage': (negative_count / total_texts * 100) if total_texts > 0 else 0,
            'neutral_percentage': (neutral_count / total_texts * 100) if total_texts > 0 else 0,
            'average_sentiment': avg_compound
        }
    }

# Reporting functions
async def generate_report(report_type: str, business_id: int, start_date: datetime, end_date: datetime, 
                       format: str, parameters: Dict[str, Any], db: Session):
    """Generate reports in various formats"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # This is a simplified implementation - in a real application, you'd fetch actual data
    # For demo purposes, we'll create synthetic report data
    
    # Generate report data based on report_type
    if report_type == "sales":
        # Generate synthetic sales data
        date_range = pd.date_range(start=start_date, end=end_date)
        np.random.seed(42)
        
        data = {
            'date': date_range,
            'sales': np.random.uniform(500, 2000, size=len(date_range)),
            'orders': np.random.randint(5, 50, size=len(date_range)),
            'average_order_value': np.random.uniform(50, 200, size=len(date_range))
        }
        
        df = pd.DataFrame(data)
        
        # Format dates
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # Create the report based on the requested format
        if format.lower() == 'csv':
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return buffer.getvalue(), 'text/csv'
            
        elif format.lower() == 'xlsx':
            buffer = io.BytesIO()
            
            # Create a more elaborate Excel report with charts
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sales Data', index=False)
                
                # Access the XlsxWriter workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Sales Data']
                
                # Create a chart
                chart = workbook.add_chart({'type': 'line'})
                
                # Configure the chart
                chart.add_series({
                    'name': 'Sales',
                    'categories': ['Sales Data', 1, 0, len(df), 0],
                    'values': ['Sales Data', 1, 1, len(df), 1],
                })
                
                # Add the chart to the worksheet
                worksheet.insert_chart('F2', chart)
                
                # Add summary statistics
                summary_data = {
                    'Metric': ['Total Sales', 'Total Orders', 'Average Order Value'],
                    'Value': [df['sales'].sum(), df['orders'].sum(), df['sales'].sum() / df['orders'].sum()]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            buffer.seek(0)
            return buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        elif format.lower() == 'pdf':
            # Generate a PDF report (simplified - in a real app, you'd use a PDF library)
            # For demo purposes, we'll generate an HTML representation
            html_content = f"""
            <html>
              <head>
                <title>Sales Report</title>
                <style>
                  body {{ font-family: Arial, sans-serif; }}
                  h1 {{ color: #2c3e50; }}
                  table {{ border-collapse: collapse; width: 100%; }}
                  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                  th {{ background-color: #f2f2f2; }}
                </style>
              </head>
              <body>
                <h1>Sales Report for {business.name}</h1>
                <p>Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
                
                <h2>Summary</h2>
                <table>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                  </tr>
                  <tr>
                    <td>Total Sales</td>
                    <td>${df['sales'].sum():.2f}</td>
                  </tr>
                  <tr>
                    <td>Total Orders</td>
                    <td>{df['orders'].sum()}</td>
                  </tr>
                  <tr>
                    <td>Average Order Value</td>
                    <td>${df['sales'].sum() / df['orders'].sum():.2f}</td>
                  </tr>
                </table>
                
                <h2>Daily Sales</h2>
                <table>
                  <tr>
                    <th>Date</th>
                    <th>Sales</th>
                    <th>Orders</th>
                    <th>Avg. Order Value</th>
                  </tr>
            """
            
            for _, row in df.iterrows():
                html_content += f"""
                  <tr>
                    <td>{row['date']}</td>
                    <td>${row['sales']:.2f}</td>
                    <td>{row['orders']}</td>
                    <td>${row['average_order_value']:.2f}</td>
                  </tr>
                """
                
            html_content += """
                </table>
              </body>
            </html>
            """
            
            # In a real application, you'd convert this HTML to PDF
            # For the demo, we'll just return the HTML
            return html_content, 'text/html'
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported report format: {format}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported report type: {report_type}")

# API Endpoints
@app.get("/")
def home():
    return {
        "message": "Welcome to AI-Powered E-Commerce Manager API",
        "version": "2.0.0",
        "documentation": "/docs"
    }

# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is enabled
    if user.mfa_enabled:
        # In a real app, you'd handle MFA verification here
        # For demo purposes, we'll skip this step
        pass
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id, "is_superuser": user.is_superuser},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "id": user.id, "is_superuser": user.is_superuser}
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "expires_at": datetime.utcnow() + access_token_expires,
        "user_id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser
    }

@app.post("/token/refresh", response_model=Token)
async def refresh_token(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        is_superuser: bool = payload.get("is_superuser", False)
        if username is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id, "is_superuser": user.is_superuser},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "id": user.id, "is_superuser": user.is_superuser}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "expires_at": datetime.utcnow() + access_token_expires,
        "user_id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser
    }

# User management endpoints
@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_username = db.query(User).filter(User.username == user.username).first()
    if db_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@app.put("/users/me", response_model=UserOut)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    if user_update.email:
        db_user = db.query(User).filter(User.email == user_update.email).first()
        if db_user and db_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_update.email
    
    if user_update.full_name:
        current_user.full_name = user_update.full_name
    
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    if user_update.is_active is not None:
        current_user.is_active = user_update.is_active
    
    if user_update.avatar_url:
        current_user.avatar_url = user_update.avatar_url
    
    if user_update.preferences:
        # Merge with existing preferences, don't overwrite
        current_prefs = current_user.preferences or {}
        current_prefs.update(user_update.preferences)
        current_user.preferences = current_prefs
    
    db.commit()
    db.refresh(current_user)
    return current_user

@app.post("/users/me/mfa", response_model=dict)
async def setup_mfa(
    mfa_setup: MFASetup,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Setup or disable MFA for current user"""
    if mfa_setup.enable:
        # Generate a new MFA secret if one doesn't exist
        if not current_user.mfa_secret:
            current_user.mfa_secret = generate_mfa_secret()
            db.commit()
        
        # Generate provisioning URI for QR code
        totp = pyotp.TOTP(current_user.mfa_secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name="AI E-Commerce Manager"
        )
        
        return {
            "message": "MFA setup initiated",
            "secret": current_user.mfa_secret,
            "provisioning_uri": provisioning_uri
        }
    else:
        # Verify token before disabling MFA
        if mfa_setup.token and current_user.mfa_enabled:
            if not verify_mfa_token(current_user, mfa_setup.token):
                raise HTTPException(status_code=400, detail="Invalid MFA token")
        
        current_user.mfa_enabled = False
        db.commit()
        return {"message": "MFA disabled successfully"}

@app.post("/users/me/mfa/verify", response_model=dict)
async def verify_mfa(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify MFA token and enable MFA for user"""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up")
    
    if verify_mfa_token(current_user, token):
        current_user.mfa_enabled = True
        db.commit()
        return {"message": "MFA enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid MFA token")

# Business management endpoints
@app.post("/businesses/", response_model=BusinessOut)
async def add_business(
    business: BusinessCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new business for a user"""
    # Create new business
    platform_details = business.platform_details or {}
    settings = business.settings or {}
    
    db_business = Business(
        user_id=current_user.id,
        platform_type=business.platform_type,
        name=business.name,
        platform_url=business.platform_url,
        platform_token=business.platform_token,
        platform_details=platform_details,
        settings=settings
    )
    
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    
    # Check for achievements
    achievement = check_achievements(current_user.id, db)
    
    return db_business

@app.get("/businesses/", response_model=List[BusinessOut])
async def get_businesses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all businesses for a user"""
    businesses = db.query(Business).filter(Business.user_id == current_user.id).all()
    return businesses

@app.get("/businesses/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details for a specific business"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business

@app.put("/businesses/{business_id}", response_model=BusinessOut)
async def update_business(
    business_id: int,
    business_update: BusinessUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a business"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields if provided
    if business_update.name:
        business.name = business_update.name
    if business_update.platform_url:
        business.platform_url = business_update.platform_url
    if business_update.platform_token:
        business.platform_token = business_update.platform_token
    if business_update.platform_details:
        # Merge with existing details, don't overwrite
        current_details = business.platform_details or {}
        current_details.update(business_update.platform_details)
        business.platform_details = current_details
    if business_update.settings:
        # Merge with existing settings, don't overwrite
        current_settings = business.settings or {}
        current_settings.update(business_update.settings)
        business.settings = current_settings
    
    business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(business)
    
    return business

@app.delete("/businesses/{business_id}")
async def delete_business(
    business_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a business"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    db.delete(business)
    db.commit()
    
    return {"message": "Business deleted successfully"}

# Product management endpoints
@app.get("/businesses/{business_id}/products")
async def get_products(
    business_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetch products from a business"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        # Connect to the appropriate platform
        connect_to_platform(business)
        
        # Fetch products based on platform type
        if business.platform_type.lower() == "shopify":
            products = shopify.Product.find(limit=limit, offset=offset)
            return {"products": [p.to_dict() for p in products]}
        elif business.platform_type.lower() in ["bigcommerce", "magento", "etsy", "woocommerce"]:
            # Placeholder for other platforms
            # In a real app, you'd implement the API calls for each platform
            return {"message": f"Fetching products from {business.platform_type} will be implemented soon."}
        else:
            raise HTTPException(status_code=400, detail=f"Product fetching not implemented for {business.platform_type}")
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")

# AI Optimization endpoints
@app.post("/businesses/{business_id}/optimize")
async def optimize_store(
    business_id: int,
    optimization: OptimizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI-powered store optimization for different business types"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Initialize response
    suggestions = {}
    
    # Platform-specific optimizations
    if business.platform_type.lower() == "shopify":
        try:
            # Connect to Shopify
            connect_to_shopify(business.platform_url, business.platform_token)
            
            # Different optimization types
            if optimization.optimization_type == "categories":
                # Get products for categorization
                products = shopify.Product.find()
                product_data = [{"id": p.id, "title": p.title, "description": p.body_html} for p in products]
                
                # AI categorization
                ai_prompt = f"Analyze the following products and suggest category improvements:\n{product_data}"
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                suggestions["categories"] = response["choices"][0]["message"]["content"]
                
            elif optimization.optimization_type == "pricing":
                # Get products for pricing optimization
                products = shopify.Product.find()
                product_data = [{"id": p.id, "title": p.title, "price": p.variants[0].price} for p in products]
                
                # AI pricing optimization
                ai_prompt = f"Analyze the following products and suggest pricing improvements:\n{product_data}"
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                suggestions["pricing"] = response["choices"][0]["message"]["content"]
                
            elif optimization.optimization_type == "seo":
                # Get products for SEO optimization
                products = shopify.Product.find()
                product_data = [{"id": p.id, "title": p.title, "description": p.body_html} for p in products]
                
                # AI SEO optimization
                ai_prompt = f"Analyze the following products and suggest SEO improvements for titles and descriptions:\n{product_data}"
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                suggestions["seo"] = response["choices"][0]["message"]["content"]
                
            elif optimization.optimization_type == "store_design":
                # In a real app, you'd fetch the store theme and settings
                # For the demo, we'll use a generic prompt
                ai_prompt = "Suggest improvements for a Shopify store design to maximize conversions and user engagement."
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                suggestions["store_design"] = response["choices"][0]["message"]["content"]
                
            elif optimization.optimization_type == "marketing":
                # Get customer data for marketing optimization
                customers = shopify.Customer.find()
                customer_data = [{"id": c.id, "email": c.email, "orders_count": c.orders_count} for c in customers]
                
                # AI marketing optimization
                ai_prompt = f"Analyze the following customer data and suggest marketing campaign improvements:\n{customer_data}"
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                suggestions["marketing"] = response["choices"][0]["message"]["content"]
                
            else:
                return {"error": f"Optimization type '{optimization.optimization_type}' not supported"}
                
        except Exception as e:
            logger.error(f"Error optimizing store: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error optimizing store: {str(e)}")
            
    elif business.platform_type.lower() == "affiliate":
        # Handle affiliate optimization
        platform_details = business.platform_details or {}
        
        # Generic affiliate optimization using AI
        ai_prompt = f"Suggest optimizations for an affiliate marketing business with the following details:\n{platform_details}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": ai_prompt}]
        )
        
        suggestions["affiliate_optimization"] = response["choices"][0]["message"]["content"]
        
    elif business.platform_type.lower() in ["bigcommerce", "magento", "etsy", "woocommerce"]:
        # Handle other platform optimizations
        ai_prompt = f"Suggest optimizations for a {business.platform_type} store named {business.name}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": ai_prompt}]
        )
        
        suggestions["platform_optimization"] = response["choices"][0]["message"]["content"]
        
    else:
        # Generic business optimization
        ai_prompt = f"Suggest optimizations for a {business.platform_type} business named {business.name}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": ai_prompt}]
        )
        
        suggestions["general_optimization"] = response["choices"][0]["message"]["content"]
    
    return {"business_id": business_id, "suggestions": suggestions}

@app.post("/businesses/{business_id}/implement")
async def implement_changes(
    business_id: int,
    changes: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Implement AI-suggested changes after user approval"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Initialize response
    implementation_results = {"success": [], "failed": []}
    
    # Implement for specific platform types
    if business.platform_type.lower() == "shopify":
        try:
            # Connect to Shopify
            connect_to_shopify(business.platform_url, business.platform_token)
            
            # Implement category changes
            if "categories" in changes:
                for category_change in changes["categories"]:
                    try:
                        # Logic to implement category changes via Shopify API
                        product_id = category_change["product_id"]
                        new_category = category_change["new_category"]
                        
                        # Fetch product
                        product = shopify.Product.find(product_id)
                        
                        # Update product category
                        product.product_type = new_category
                        product.save()
                        
                        implementation_results["success"].append({
                            "type": "category",
                            "product_id": product_id,
                            "new_value": new_category
                        })
                    except Exception as e:
                        implementation_results["failed"].append({
                            "type": "category",
                            "product_id": category_change["product_id"],
                            "error": str(e)
                        })
            
            # Implement pricing changes
            if "pricing" in changes:
                for price_change in changes["pricing"]:
                    try:
                        # Logic to implement price changes via Shopify API
                        product_id = price_change["product_id"]
                        variant_id = price_change.get("variant_id", None)
                        new_price = price_change["new_price"]
                        
                        # Fetch product
                        product = shopify.Product.find(product_id)
                        
                        # Update price (either specific variant or first variant)
                        if variant_id:
                            for variant in product.variants:
                                if str(variant.id) == str(variant_id):
                                    variant.price = new_price
                                    break
                        else:
                            product.variants[0].price = new_price
                        
                        product.save()
                        
                        implementation_results["success"].append({
                            "type": "price",
                            "product_id": product_id,
                            "variant_id": variant_id,
                            "new_value": new_price
                        })
                    except Exception as e:
                        implementation_results["failed"].append({
                            "type": "price",
                            "product_id": price_change["product_id"],
                            "error": str(e)
                        })
            
            # Implement SEO changes
            if "seo" in changes:
                for seo_change in changes["seo"]:
                    try:
                        # Logic to implement SEO changes via Shopify API
                        product_id = seo_change["product_id"]
                        new_title = seo_change.get("new_title", None)
                        new_description = seo_change.get("new_description", None)
                        new_meta_tags = seo_change.get("new_meta_tags", None)
                        
                        # Fetch product
                        product = shopify.Product.find(product_id)
                        
                        # Update SEO elements
                        if new_title:
                            product.title = new_title
                        if new_description:
                            product.body_html = new_description
                        if new_meta_tags:
                            # This is simplified - actual implementation would depend on Shopify's data structure
                            product.metafields_global_title_tag = new_meta_tags.get("title_tag", "")
                            product.metafields_global_description_tag = new_meta_tags.get("description_tag", "")
                        
                        product.save()
                        
                        implementation_results["success"].append({
                            "type": "seo",
                            "product_id": product_id,
                            "fields_updated": {
                                "title": bool(new_title),
                                "description": bool(new_description),
                                "meta_tags": bool(new_meta_tags)
                            }
                        })
                    except Exception as e:
                        implementation_results["failed"].append({
                            "type": "seo",
                            "product_id": seo_change["product_id"],
                            "error": str(e)
                        })
                        
        except Exception as e:
            logger.error(f"Error implementing changes: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error implementing changes: {str(e)}")
    
    elif business.platform_type.lower() in ["bigcommerce", "magento", "etsy", "woocommerce"]:
        # For other platforms, return that implementation is not fully supported yet
        return {
            "message": f"Automated implementation for {business.platform_type} is in development.",
            "manual_instructions": "Please follow these steps to implement the changes manually: [Instructions would be generated here]"
        }
    
    else:
        # For non-supported platforms
        return {
            "message": f"Automated implementation not supported for {business.platform_type} platform.",
            "manual_instructions": "Please follow these steps to implement the changes manually: [Instructions would be generated here]"
        }
    
    return implementation_results

# AI Analysis endpoints
@app.post("/businesses/{business_id}/predict")
async def predict(
    business_id: int,
    prediction_req: PredictionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI-powered predictions based on business data"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Run the appropriate prediction based on prediction_type
    if prediction_req.prediction_type == "sales":
        return predict_sales(
            business_id=business_id,
            timeframe=prediction_req.timeframe,
            parameters=prediction_req.parameters or {},
            db=db
        )
    elif prediction_req.prediction_type == "inventory":
        # Placeholder for inventory prediction
        return {"message": "Inventory prediction not implemented yet"}
    elif prediction_req.prediction_type == "customer_behavior":
        # Placeholder for customer behavior prediction
        return {"message": "Customer behavior prediction not implemented yet"}
    else:
        raise HTTPException(status_code=400, detail=f"Prediction type '{prediction_req.prediction_type}' not supported")

@app.post("/businesses/{business_id}/sentiment")
async def analyze_sentiment_endpoint(
    business_id: int,
    request: SentimentAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Analyze sentiment of customer reviews or social media posts"""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # If text data is provided directly, analyze it
    if request.text_data:
        return analyze_sentiment(request.text_data)
    
    # If product IDs are provided, fetch reviews from the platform
    elif request.product_ids and business.platform_type.lower() == "shopify":
        try:
            # Connect to Shopify
            connect_to_shopify(business.platform_url, business.platform_token)
            
            # This is a simplified example - in a real app, you'd fetch actual reviews
            # For demo purposes, we'll create synthetic reviews
            reviews = []
            for product_id in request.product_ids:
                # Generate some synthetic reviews
                synthetic_reviews = [
                    f"I love this product! It works exactly as described and arrived quickly.",
                    f"Decent product but a bit overpriced for what you get.",
                    f"Not what I expected. The quality is lower than advertised.",
                    f"Amazing customer service and the product is great too!",
                    f"This product changed my life! Highly recommend to everyone."
                ]
                reviews.extend(synthetic_reviews)
            
            return analyze_sentiment(reviews)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")
    
    # If source is social media, fetch posts from social platforms
    elif request.source == "social_media":
        # In a real app, you'd connect to social media APIs
        # For demo purposes, we'll create synthetic social media posts
        social_posts = [
            f"Just got my new purchase from {business.name} and I'm loving it! #happy #shopping",
            f"Disappointed with my recent order from {business.name}. Not as advertised. #unhappy",
            f"The customer service at {business.name} is excellent! They resolved my issue quickly.",
            f"Mixed feelings about {business.name} products. Some are great, others not so much.",
            f"Can't say enough good things about {business.name}! Will definitely shop again."
        ]
        
        return analyze_sentiment(social_posts)
    
    else:
        raise HTTPException(status_code=400, detail="Please provide text_data, product_ids, or specify a source")

# Dashboard management endpoints
@app.post("/dashboards/")
async def create_dashboard(
    dashboard: DashboardCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new dashboard for a business"""
    # Check if business exists and belongs to user
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Create the dashboard
    new_dashboard = Dashboard(
        business_id=dashboard.business_id,
        name=dashboard.name,
        layout=dashboard.layout or {},
        is_default=dashboard.is_default
    )
    
    # If this is set as default, update any existing default dashboards
    if dashboard.is_default:
        existing_defaults = db.query(Dashboard).filter(
            Dashboard.business_id == dashboard.business_id,
            Dashboard.is_default == True
        ).all()
        
        for d in existing_defaults:
            d.is_default = False
    
    db.add(new_dashboard)
    db.commit()
    db.refresh(new_dashboard)
    
    return new_dashboard

@app.get("/businesses/{business_id}/dashboards")
async def get_dashboards(
    business_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all dashboards for a business"""
    # Check if business exists and belongs to user
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get the dashboards
    dashboards = db.query(Dashboard).filter(Dashboard.business_id == business_id).all()
    
    return dashboards

@app.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific dashboard with its widgets"""
    # Get the dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Check if user has access to this dashboard
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the widgets
    widgets = db.query(Widget).filter(Widget.dashboard_id == dashboard_id).all()
    
    return {
        "dashboard": dashboard,
        "widgets": widgets
    }

@app.put("/dashboards/{dashboard_id}")
async def update_dashboard(
    dashboard_id: int,
    dashboard_update: DashboardUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a dashboard"""
    # Get the dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Check if user has access to this dashboard
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update the dashboard
    if dashboard_update.name:
        dashboard.name = dashboard_update.name
    
    if dashboard_update.layout is not None:
        dashboard.layout = dashboard_update.layout
    
    if dashboard_update.is_default is not None:
        # If setting as default, update any existing defaults
        if dashboard_update.is_default and not dashboard.is_default:
            existing_defaults = db.query(Dashboard).filter(
                Dashboard.business_id == dashboard.business_id,
                Dashboard.is_default == True
            ).all()
            
            for d in existing_defaults:
                d.is_default = False
        
        dashboard.is_default = dashboard_update.is_default
    
    dashboard.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dashboard)
    
    return dashboard

@app.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a dashboard"""
    # Get the dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Check if user has access to this dashboard
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete all widgets first
    db.query(Widget).filter(Widget.dashboard_id == dashboard_id).delete()
    
    # Delete the dashboard
    db.delete(dashboard)
    db.commit()
    
    return {"message": "Dashboard deleted successfully"}

# Widget management endpoints
@app.post("/widgets/")
async def create_widget(
    widget: WidgetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new widget for a dashboard"""
    # Get the dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Check if user has access to this dashboard
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create the widget
    new_widget = Widget(
        dashboard_id=widget.dashboard_id,
        widget_type=widget.widget_type,
        title=widget.title,
        settings=widget.settings or {},
        position=widget.position or {"x": 0, "y": 0, "w": 3, "h": 2}
    )
    
    db.add(new_widget)
    db.commit()
    db.refresh(new_widget)
    
    return new_widget

@app.put("/widgets/{widget_id}")
async def update_widget(
    widget_id: int,
    widget_update: WidgetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a widget"""
    # Get the widget
    widget = db.query(Widget).filter(Widget.id == widget_id).first()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # Check if user has access to this widget's dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update the widget
    if widget_update.title:
        widget.title = widget_update.title
    
    if widget_update.settings:
        # Merge with existing settings
        current_settings = widget.settings or {}
        current_settings.update(widget_update.settings)
        widget.settings = current_settings
    
    if widget_update.position:
        # Merge with existing position
        current_position = widget.position or {}
        current_position.update(widget_update.position)
        widget.position = current_position
    
    db.commit()
    db.refresh(widget)
    
    return widget

@app.delete("/widgets/{widget_id}")
async def delete_widget(
    widget_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a widget"""
    # Get the widget
    widget = db.query(Widget).filter(Widget.id == widget_id).first()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # Check if user has access to this widget's dashboard
    dashboard = db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
    business = db.query(Business).filter(
        Business.id == dashboard.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete the widget
    db.delete(widget)
    db.commit()
    
    return {"message": "Widget deleted successfully"}

# A/B Testing endpoints
@app.post("/ab-tests/")
async def create_ab_test(
    ab_test: ABTestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new A/B test for a business"""
    # Check if business exists and belongs to user
    business = db.query(Business).filter(
        Business.id == ab_test.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Create the A/B test
    new_ab_test = ABTest(
        business_id=ab_test.business_id,
        name=ab_test.name,
        description=ab_test.description,
        start_date=ab_test.start_date,
        end_date=ab_test.end_date,
        test_type=ab_test.test_type,
        variants=ab_test.variants
    )
    
    db.add(new_ab_test)
    db.commit()
    db.refresh(new_ab_test)
    
    return new_ab_test

@app.get("/businesses/{business_id}/ab-tests")
async def get_ab_tests(
    business_id: int,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all A/B tests for a business"""
    # Check if business exists and belongs to user
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get the A/B tests
    query = db.query(ABTest).filter(ABTest.business_id == business_id)
    
    if status:
        query = query.filter(ABTest.status == status)
    
    ab_tests = query.all()
    
    return ab_tests

@app.get("/ab-tests/{ab_test_id}")
async def get_ab_test(
    ab_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific A/B test"""
    # Get the A/B test
    ab_test = db.query(ABTest).filter(ABTest.id == ab_test_id).first()
    
    if not ab_test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Check if user has access to this A/B test
    business = db.query(Business).filter(
        Business.id == ab_test.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ab_test

@app.put("/ab-tests/{ab_test_id}")
async def update_ab_test(
    ab_test_id: int,
    ab_test_update: ABTestUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an A/B test"""
    # Get the A/B test
    ab_test = db.query(ABTest).filter(ABTest.id == ab_test_id).first()
    
    if not ab_test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Check if user has access to this A/B test
    business = db.query(Business).filter(
        Business.id == ab_test.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update the A/B test
    if ab_test_update.name:
        ab_test.name = ab_test_update.name
    
    if ab_test_update.description is not None:
        ab_test.description = ab_test_update.description
    
    if ab_test_update.start_date:
        ab_test.start_date = ab_test_update.start_date
    
    if ab_test_update.end_date is not None:
        ab_test.end_date = ab_test_update.end_date
    
    if ab_test_update.status:
        ab_test.status = ab_test_update.status
    
    if ab_test_update.variants:
        ab_test.variants = ab_test_update.variants
    
    if ab_test_update.results is not None:
        ab_test.results = ab_test_update.results
    
    if ab_test_update.winner_variant is not None:
        ab_test.winner_variant = ab_test_update.winner_variant
    
    ab_test.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ab_test)
    
    return ab_test

@app.delete("/ab-tests/{ab_test_id}")
async def delete_ab_test(
    ab_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an A/B test"""
    # Get the A/B test
    ab_test = db.query(ABTest).filter(ABTest.id == ab_test_id).first()
    
    if not ab_test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    # Check if user has access to this A/B test
    business = db.query(Business).filter(
        Business.id == ab_test.business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete the A/B test
    db.delete(ab_test)
    db.commit()
    
    return {"message": "A/B test deleted successfully"}

# Feedback endpoints
@app.post("/feedback/")
async def create_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new feedback entry"""
    new_feedback = Feedback(
        user_id=current_user.id,
        content=feedback.content,
        feedback_type=feedback.feedback_type
    )
    
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    
    return new_feedback

@app.get("/feedback/")
async def get_feedback(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all feedback entries for the current user"""
    feedback_entries = db.query(Feedback).filter(Feedback.user_id == current_user.id).all()
    return feedback_entries

# Reporting endpoints
@app.post("/businesses/{business_id}/reports")
async def generate_report_endpoint(
    business_id: int,
    report_request: ReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a report for a business"""
    # Check if business exists and belongs to user
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Generate the report
    try:
        report_content, content_type = await generate_report(
            report_type=report_request.report_type,
            business_id=business_id,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            format=report_request.format,
            parameters=report_request.parameters or {},
            db=db
        )
        
        # For CSV and Excel, return as downloadable file
        if content_type in ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            filename = f"{report_request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if report_request.format.lower() == 'csv':
                filename += ".csv"
            elif report_request.format.lower() == 'xlsx':
                filename += ".xlsx"
            
            # Create a temporary file
            tmp_path = f"/tmp/{filename}"
            with open(tmp_path, 'wb') as f:
                f.write(report_content)
            
            return FileResponse(
                path=tmp_path,
                filename=filename,
                media_type=content_type
            )
        
        # For HTML/PDF, return as JSON with content
        else:
            return {
                "content": report_content,
                "content_type": content_type,
                "report_type": report_request.report_type,
                "business_id": business_id,
                "period": {
                    "start_date": report_request.start_date,
                    "end_date": report_request.end_date
                }
            }
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

# Achievement endpoints
@app.get("/achievements/")
async def get_achievements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all achievements for the current user"""
    user_achievements = db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()
    
    result = []
    for ua in user_achievements:
        achievement = db.query(Achievement).filter(Achievement.id == ua.achievement_id).first()
        if achievement:
            result.append({
                "id": achievement.id,
                "name": achievement.name,
                "description": achievement.description,
                "points": achievement.points,
                "badge_url": achievement.badge_url,
                "achieved_at": ua.achieved_at
            })
    
    return result

@app.get("/achievements/available")
async def get_available_achievements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all available achievements"""
    all_achievements = db.query(Achievement).all()
    user_achievements = db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()
    achieved_ids = [ua.achievement_id for ua in user_achievements]
    
    result = {
        "achieved": [],
        "not_achieved": []
    }
    
    for achievement in all_achievements:
        achievement_data = {
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "points": achievement.points,
            "badge_url": achievement.badge_url
        }
        
        if achievement.id in achieved_ids:
            ua = next((ua for ua in user_achievements if ua.achievement_id == achievement.id), None)
            achievement_data["achieved_at"] = ua.achieved_at if ua else None
            result["achieved"].append(achievement_data)
        else:
            result["not_achieved"].append(achievement_data)
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
