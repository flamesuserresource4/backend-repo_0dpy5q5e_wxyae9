import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# ==========================
# Annuaire (Employee) API
# ==========================

class EmployeeFilter(BaseModel):
    q: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    isActive: Optional[bool] = None
    tags: Optional[List[str]] = None

@app.get("/api/employees")
def list_employees(
    q: Optional[str] = Query(default=None, description="Search across name, title, department, email, phone"),
    department: Optional[str] = None,
    location: Optional[str] = None,
    isActive: Optional[bool] = None,
    tags: Optional[str] = Query(default=None, description="Comma separated tags"),
    limit: int = Query(default=200, le=500),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filter_query: dict = {}

    if q:
        # Search across multiple fields using case-insensitive regex
        filter_query["$or"] = [
            {"firstName": {"$regex": q, "$options": "i"}},
            {"lastName": {"$regex": q, "$options": "i"}},
            {"full_name": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
            {"department": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
            {"location": {"$regex": q, "$options": "i"}},
        ]

    if department:
        filter_query["department"] = department

    if location:
        filter_query["location"] = location

    if isActive is not None:
        filter_query["isActive"] = isActive

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            filter_query["tags"] = {"$all": tag_list}

    docs = get_documents("employee", filter_query, limit)

    # Normalize Mongo ObjectId and field aliases
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    
    return {"items": docs, "count": len(docs)}

@app.post("/api/employees/seed")
def seed_employees():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    sample = [
        {
            "firstName": "أمين",
            "lastName": "بن صالح",
            "full_name": "أمين بن صالح",
            "title": "مهندس نظم",
            "department": "IT",
            "email": "amine.bensaleh@example.com",
            "phone": "+213560000001",
            "office": "D3-201",
            "location": "Bab Ezzouar",
            "photoUrl": "https://i.pravatar.cc/150?img=1",
            "bio": "خبير في البنية التحتية والشبكات.",
            "tags": ["Linux", "Networking", "DevOps"],
            "isActive": True,
        },
        {
            "firstName": "ليلى",
            "lastName": "قاسم",
            "full_name": "ليلى قاسم",
            "title": "موارد بشرية",
            "department": "HR",
            "email": "leila.kacem@example.com",
            "phone": "+213560000002",
            "office": "D3-105",
            "location": "Bab Ezzouar",
            "photoUrl": "https://i.pravatar.cc/150?img=5",
            "bio": "تطوير المواهب وثقافة المؤسسة.",
            "tags": ["Recruitment", "Culture"],
            "isActive": True,
        },
        {
            "firstName": "مروان",
            "lastName": "شرقي",
            "full_name": "مروان شرقي",
            "title": "محاسب",
            "department": "Finance",
            "email": "marouane.cherki@example.com",
            "phone": "+213560000003",
            "office": "D3-009",
            "location": "Bab Ezzouar",
            "photoUrl": "https://i.pravatar.cc/150?img=8",
            "bio": "إدارة الميزانيات والتقارير.",
            "tags": ["Accounting", "Excel"],
            "isActive": True,
        },
    ]

    inserted = 0
    for s in sample:
        try:
            create_document("employee", s)
            inserted += 1
        except Exception:
            pass

    return {"inserted": inserted}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
