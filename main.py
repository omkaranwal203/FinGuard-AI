
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, csv, io, statistics, re
from datetime import datetime

DB = "finguard.db"
app = FastAPI(title="FinGuard AI API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SEED = [
    ("2026-09-25","Global Electronics","Shopping",18900,"debit"),
    ("2026-09-24","Amazon","Shopping",2499,"debit"),
    ("2026-09-23","Uber","Transport",680,"debit"),
    ("2026-09-22","Netflix","Subscriptions",649,"debit"),
    ("2026-09-20","ABC Grocers","Food",4210,"debit"),
    ("2026-09-18","Salary Credit","Income",65000,"credit"),
    ("2026-09-16","Electricity Board","Utilities",2300,"debit"),
    ("2026-09-14","Cafe Coffee","Food",520,"debit"),
    ("2026-09-12","Fuel Station","Transport",3100,"debit"),
    ("2026-09-10","Online Store","Shopping",7200,"debit"),
]

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, merchant TEXT, category TEXT,
        amount REAL, type TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, target REAL, current REAL DEFAULT 0
    )""")
    if c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO transactions(date,merchant,category,amount,type) VALUES(?,?,?,?,?)",
            SEED
        )
    if c.execute("SELECT COUNT(*) FROM goals").fetchone()[0] == 0:
        c.execute("INSERT INTO goals(name,target,current) VALUES(?,?,?)",
                  ("Emergency Fund",100000,38000))
        c.execute("INSERT INTO goals(name,target,current) VALUES(?,?,?)",
                  ("New Laptop",80000,32000))
    c.commit(); c.close()

init_db()

@app.get("/", include_in_schema=False)
def home():
    return FileResponse("index.html")

def rows():
    c=conn()
    data=[dict(x) for x in c.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()]
    c.close()
    return data

def risk_for(t, all_rows=None):
    data=all_rows or rows()
    expenses=[x["amount"] for x in data if x["type"]=="debit"]
    avg=statistics.mean(expenses) if expenses else 1
    amount=t["amount"]
    score=20
    reasons=[]
    if amount > max(avg*2.5, 10000):
        score += 50
        reasons.append("amount is unusually high")
    cat=[x["amount"] for x in data if x["category"]==t["category"] and x["type"]=="debit" and x["id"]!=t["id"]]
    if cat:
        ca=statistics.mean(cat)
        if amount > ca*2:
            score += 20
            reasons.append("above your category average")
    merchant_count=sum(1 for x in data if x["merchant"].lower()==t["merchant"].lower())
    if merchant_count <= 1 and t["type"]=="debit":
        score += 15
        reasons.append("new merchant in your history")
    if score >= 70: level="high"
    elif score >= 45: level="medium"
    else: level="low"
    return {
        "score": min(score,99),
        "level": level,
        "reasons": reasons or ["pattern is consistent with your recent activity"]
    }

def enriched():
    data=rows()
    return [{**t, "risk": risk_for(t,data)} for t in data]

@app.get("/api/health")
def health(): return {"status":"ok","service":"FinGuard AI API"}

@app.get("/api/dashboard")
def dashboard():
    data=enriched()
    balance=sum(x["amount"] for x in data if x["type"]=="credit")-sum(x["amount"] for x in data if x["type"]=="debit")
    high=sum(x["risk"]["level"]=="high" for x in data)
    med=sum(x["risk"]["level"]=="medium" for x in data)
    spending=sum(x["amount"] for x in data if x["type"]=="debit")
    return {
        "balance": balance,
        "spending": spending,
        "riskAlerts": high+med,
        "highRisk": high,
        "mediumRisk": med,
        "healthScore": max(0, min(100, 100-high*12-med*4)),
        "transactions": len(data),
        "alerts": [x for x in data if x["risk"]["level"] in ("high","medium")][:5]
    }

@app.get("/api/transactions")
def transactions(q: str="", risk: str="all"):
    data=enriched()
    q=q.lower().strip()
    out=[]
    for x in data:
        if q and q not in (x["merchant"]+" "+x["category"]).lower(): continue
        if risk!="all" and x["risk"]["level"]!=risk: continue
        out.append(x)
    return out

@app.get("/api/transactions/{tid}")
def transaction_detail(tid:int):
    c=conn(); r=c.execute("SELECT * FROM transactions WHERE id=?",(tid,)).fetchone(); c.close()
    if not r: return {"error":"Transaction not found"}
    t=dict(r); t["risk"]=risk_for(t)
    r=t["risk"]
    t["solution"] = solution_for(r["level"], t)
    return t

def solution_for(level,t):
    if level=="high":
        return [
            "Verify the merchant and payment receipt immediately.",
            "If you do not recognize it, contact your bank/card issuer and freeze the affected card.",
            "Do not share OTP, PIN or CVV with anyone.",
            "Keep a record of the transaction and report it through the bank's official fraud channel."
        ]
    if level=="medium":
        return [
            "Review the transaction against your recent spending.",
            "Confirm that the amount and merchant are expected.",
            "If recurring, check whether the subscription or bill has changed.",
            "Monitor the category for the next 7 days."
        ]
    return [
        "No immediate action is indicated by the demo risk engine.",
        "Continue monitoring your normal spending pattern.",
        "Keep alerts enabled for unusual activity."
    ]

@app.get("/api/risks")
def risks():
    out=[]
    for t in enriched():
        if t["risk"]["level"]!="low":
            out.append({
                "transaction":t,
                "solution":solution_for(t["risk"]["level"],t),
                "priority": "Immediate review" if t["risk"]["level"]=="high" else "Monitor"
            })
    return out

@app.get("/api/analysis")
def analysis():
    data=enriched()
    high=[x for x in data if x["risk"]["level"]=="high"]
    med=[x for x in data if x["risk"]["level"]=="medium"]
    return {
        "fraudProbability": min(95, 35+len(high)*18),
        "cashFlowPressure": min(90, 30+len(med)*10),
        "stabilityScore": max(0,100-len(high)*15-len(med)*5),
        "topRisk": high[0] if high else (med[0] if med else None),
        "method":"Rule-based explainable anomaly engine (prototype)"
    }

@app.get("/api/forecast")
def forecast():
    data=rows()
    income=sum(x["amount"] for x in data if x["type"]=="credit")
    expense=sum(x["amount"] for x in data if x["type"]=="debit")
    net=income-expense
    current=net
    months=["Oct","Nov","Dec","Jan","Feb","Mar"]
    values=[]
    for i,m in enumerate(months):
        current += net*0.12
        values.append(round(current))
    return {"months":months,"projected":values,"threshold":90000}

class Chat(BaseModel):
    message:str

@app.post("/api/assistant")
def assistant(body:Chat):
    q=body.message.lower()
    d=dashboard()
    if any(w in q for w in ["fraud","risk","alert","suspicious"]):
        answer=f"The highest-priority signal is {d['highRisk']} high-risk and {d['mediumRisk']} medium-risk transaction(s). Open Risk Center to see the reason and action plan."
    elif any(w in q for w in ["save","saving","spend","expense"]):
        answer=f"Your demo spending is ₹{d['spending']:,.0f}. Start by reviewing high-value Shopping/Subscriptions transactions and set a monthly spending goal."
    elif any(w in q for w in ["cash","forecast","future"]):
        answer="The forecast uses your recent income/expense pattern. If projected balance approaches your safety threshold, reduce discretionary spending and keep a cash buffer."
    else:
        answer=f"Your current demo balance is ₹{d['balance']:,.0f}, spending is ₹{d['spending']:,.0f}, and the AI health score is {d['healthScore']}/100. Ask me about risk, saving, spending or cash flow."
    return {"answer":answer}

@app.post("/api/import")
async def import_csv(file:UploadFile=File(...)):
    raw=await file.read()
    text=raw.decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(text))
    fields={x.lower():x for x in (reader.fieldnames or [])}
    needed=["date","merchant","category","amount"]
    if not all(x in fields for x in needed):
        return {"ok":False,"error":"CSV must contain date, merchant, category and amount columns."}
    c=conn(); count=0
    for row in reader:
        amount=float(re.sub(r"[^0-9.-]","",row[fields["amount"]] or "0") or 0)
        c.execute("INSERT INTO transactions(date,merchant,category,amount,type) VALUES(?,?,?,?,?)",
                  (row[fields["date"]],row[fields["merchant"]],row[fields["category"]],amount,"debit"))
        count+=1
    c.commit(); c.close()
    return {"ok":True,"imported":count}

@app.get("/api/goals")
def get_goals():
    c=conn(); g=[dict(x) for x in c.execute("SELECT * FROM goals ORDER BY id").fetchall()]; c.close()
    for x in g: x["percent"]=round((x["current"]/x["target"]*100) if x["target"] else 0)
    return g

class Goal(BaseModel):
    name:str
    target:float
    current:float=0

@app.post("/api/goals")
def add_goal(g:Goal):
    c=conn(); cur=c.execute("INSERT INTO goals(name,target,current) VALUES(?,?,?)",(g.name,g.target,g.current)); c.commit()
    item=dict(c.execute("SELECT * FROM goals WHERE id=?",(cur.lastrowid,)).fetchone()); c.close()
    item["percent"]=round(item["current"]/item["target"]*100 if item["target"] else 0)
    return item

@app.get("/api/report")
def report():
    d=dashboard(); risks=__import__("json").loads(__import__("json").dumps(risks()))
    return {"title":"FinGuard AI Financial Report","generatedAt":datetime.now().isoformat(),"dashboard":d,"risks":risks}

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=int(os.environ.get("PORT","8000")))
