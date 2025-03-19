from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
import shopify
import openai
import os
from typing import List, Optional
import json

# FastAPI app instance
app = FastAPI(title="AI E-Commerce Manager")

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

# API Keys
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "your_shopify_api_key")
SHOPIFY_SECRET = os.getenv("SHOPIFY_SECRET", "your_shopify_secret")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # In production, store hashed passwords
    businesses = relationship("Business", back_populates="owner")

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform_type = Column(String)  # Shopify, Affiliate, etc.
    name = Column(String)
    platform_url = Column(String)
    platform_token = Column(String)
    platform_details = Column(Text)  # JSON string with platform-specific details
    owner = relationship("User", back_populates="businesses")

# Pydantic models for request validation
class UserCreate(BaseModel):
    email: str
    password: str

class BusinessCreate(BaseModel):
    platform_type: str
    name: str
    platform_url: str
    platform_token: str
    platform_details: Optional[dict] = None

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    platform_url: Optional[str] = None
    platform_token: Optional[str] = None
    platform_details: Optional[dict] = None

class OptimizationRequest(BaseModel):
    business_id: int
    optimization_type: str  # "categories", "pricing", "seo", etc.
    parameters: Optional[dict] = None

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions for specific platforms
def connect_to_shopify(platform_url, platform_token):
    """Helper function to connect to Shopify API"""
    session = shopify.Session(platform_url, "2023-10", platform_token)
    shopify.ShopifyResource.activate_session(session)
    return session

# API Endpoints
@app.get("/")
def home():
    return {"message": "Welcome to AI-Powered E-Commerce Manager API"}

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = User(email=user.email, password=user.password)  # Implement hashing in production
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "email": db_user.email}

@app.post("/businesses/")
def add_business(business: BusinessCreate, user_id: int, db: Session = Depends(get_db)):
    """Add a new business for a user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create new business
    platform_details_str = json.dumps(business.platform_details) if business.platform_details else "{}"
    
    db_business = Business(
        user_id=user_id,
        platform_type=business.platform_type,
        name=business.name,
        platform_url=business.platform_url,
        platform_token=business.platform_token,
        platform_details=platform_details_str
    )
    
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return {
        "id": db_business.id,
        "name": db_business.name,
        "platform_type": db_business.platform_type,
        "platform_url": db_business.platform_url
    }

@app.get("/businesses/")
def get_businesses(user_id: int, db: Session = Depends(get_db)):
    """Get all businesses for a user"""
    businesses = db.query(Business).filter(Business.user_id == user_id).all()
    
    result = []
    for business in businesses:
        platform_details = json.loads(business.platform_details) if business.platform_details else {}
        result.append({
            "id": business.id,
            "name": business.name,
            "platform_type": business.platform_type,
            "platform_url": business.platform_url,
            "platform_details": platform_details
        })
    
    return {"businesses": result}

@app.get("/businesses/{business_id}")
def get_business(business_id: int, db: Session = Depends(get_db)):
    """Get details for a specific business"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    platform_details = json.loads(business.platform_details) if business.platform_details else {}
    
    return {
        "id": business.id,
        "name": business.name,
        "platform_type": business.platform_type,
        "platform_url": business.platform_url,
        "platform_details": platform_details
    }

@app.put("/businesses/{business_id}")
def update_business(business_id: int, business_update: BusinessUpdate, db: Session = Depends(get_db)):
    """Update a business"""
    db_business = db.query(Business).filter(Business.id == business_id).first()
    if not db_business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields if provided
    if business_update.name:
        db_business.name = business_update.name
    if business_update.platform_url:
        db_business.platform_url = business_update.platform_url
    if business_update.platform_token:
        db_business.platform_token = business_update.platform_token
    if business_update.platform_details:
        db_business.platform_details = json.dumps(business_update.platform_details)
    
    db.commit()
    db.refresh(db_business)
    
    return {
        "id": db_business.id,
        "name": db_business.name,
        "platform_type": db_business.platform_type,
        "platform_url": db_business.platform_url
    }

@app.delete("/businesses/{business_id}")
def delete_business(business_id: int, db: Session = Depends(get_db)):
    """Delete a business"""
    db_business = db.query(Business).filter(Business.id == business_id).first()
    if not db_business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    db.delete(db_business)
    db.commit()
    
    return {"message": "Business deleted successfully"}

@app.get("/businesses/{business_id}/products")
def get_products(business_id: int, db: Session = Depends(get_db)):
    """Fetch products from a business (currently supports Shopify)"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if business.platform_type.lower() != "shopify":
        raise HTTPException(status_code=400, detail=f"Product fetching not implemented for {business.platform_type}")
    
    try:
        connect_to_shopify(business.platform_url, business.platform_token)
        products = shopify.Product.find()
        return {"products": [p.to_dict() for p in products]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")

@app.post("/businesses/{business_id}/optimize")
def optimize_store(business_id: int, optimization: OptimizationRequest, db: Session = Depends(get_db)):
    """AI-powered Store Optimization for different business types"""
    business = db.query(Business).filter(Business.id == business_id).first()
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
                
            else:
                return {"error": f"Optimization type '{optimization.optimization_type}' not supported"}
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error optimizing store: {str(e)}")
            
    elif business.platform_type.lower() == "affiliate":
        # Handle affiliate optimization
        platform_details = json.loads(business.platform_details) if business.platform_details else {}
        
        # Generic affiliate optimization using AI
        ai_prompt = f"Suggest optimizations for an affiliate marketing business with the following details:\n{platform_details}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": ai_prompt}]
        )
        
        suggestions["affiliate_optimization"] = response["choices"][0]["message"]["content"]
        
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
def implement_changes(business_id: int, changes: dict, db: Session = Depends(get_db)):
    """Implement AI-suggested changes after user approval"""
    business = db.query(Business).filter(Business.id == business_id).first()
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
                        # This is simplified - actual implementation would depend on Shopify's data structure
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
            raise HTTPException(status_code=500, detail=f"Error implementing changes: {str(e)}")
    
    else:
        # For non-Shopify platforms, return that implementation is not supported yet
        return {
            "message": f"Automated implementation not yet supported for {business.platform_type} platform.",
            "manual_instructions": "Please follow these steps to implement the changes manually: [Instructions would be generated here]"
        }
    
    return implementation_results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
