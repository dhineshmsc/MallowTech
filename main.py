import asyncio
from fastapi import FastAPI, Depends, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import models, crud, schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Configuration for Email (Replace with your actual details) ---
EMAIL_ADDRESS = "dhineshparamasivam91@gmail.com"
EMAIL_PASSWORD = "xldz veuu efjw pure" # Use app-specific passwords if available
SMTP_SERVER = "smtp.gmail.com" # e.g., smtp.gmail.com
SMTP_PORT = 587 # or 465 for SSL

# Denominations available in the shop
DENOMINATIONS = [2000, 500, 200, 100, 50, 20, 10, 5, 2, 1] # Example in INR

# --- Helper Functions ---
def calculate_change_denominations(balance: float, available_denominations: List[int]) -> Dict[int, int]:
    change_breakdown = {}
    remaining_balance = int(balance) # Work with integers for denominations

    for denom in sorted(available_denominations, reverse=True):
        if remaining_balance >= denom:
            count = remaining_balance // denom
            change_breakdown[denom] = count
            remaining_balance %= denom
    return change_breakdown

async def send_invoice_email(customer_email: str, invoice_details: str):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = customer_email
    msg['Cc'] = "dhineshmsc2014@gmail.com"   # Add your copy here
    msg['Subject'] = "Your Purchase Invoice"
    msg.attach(MIMEText(invoice_details, 'html'))

    # Combine main and CC recipients for sending
    recipients = [customer_email, "dhineshmsc2014@gmail.com"]

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg, to_addrs=recipients)
        print(f"Invoice email sent successfully to {customer_email} (CC to dhineshmsc2014@gmail.com)")
    except Exception as e:
        print(f"Failed to send email to {customer_email}: {e}")

# --- Routes ---

@app.on_event("startup")
async def startup_event():
    """Seeds initial product data if the database is empty."""
    db = next(get_db())
    if not crud.get_products(db):
        print("Seeding initial product data...")
        crud.create_product(db, schemas.ProductCreate(name="Laptop", product_id="P001", available_stocks=50, price=1200.00, tax_percentage=18.0))
        crud.create_product(db, schemas.ProductCreate(name="Mouse", product_id="P002", available_stocks=200, price=25.00, tax_percentage=18.0))
        crud.create_product(db, schemas.ProductCreate(name="Keyboard", product_id="P003", available_stocks=100, price=75.00, tax_percentage=18.0))
        crud.create_product(db, schemas.ProductCreate(name="Monitor", product_id="P004", available_stocks=30, price=300.00, tax_percentage=18.0))
        crud.create_product(db, schemas.ProductCreate(name="Webcam", product_id="P005", available_stocks=150, price=50.00, tax_percentage=18.0))
        crud.create_product(db, schemas.ProductCreate(name="Speaker", product_id="P006", available_stocks=80, price=80.00, tax_percentage=12.0))
        print("Product data seeded.")
    db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)): # Add db dependency
    recent_purchases = crud.get_recent_purchases(db, limit=10) # Fetch recent purchases
    return templates.TemplateResponse(
        "dashboard.html", # Render the new dashboard template
        {
            "request": request,
            "recent_purchases": recent_purchases # Pass the data to the template
        }
    )
# --- Product CRUD (Admin Pages) ---
@app.get("/products/", response_class=HTMLResponse)
async def list_products(request: Request, db: Session = Depends(get_db)):
    products = crud.get_products(db)
    return templates.TemplateResponse("products.html", {"request": request, "products": products})

@app.get("/products/add/", response_class=HTMLResponse)
async def add_product_form(request: Request):
    return templates.TemplateResponse("add_product.html", {"request": request, "errors": {}})

@app.post("/products/add/", response_class=HTMLResponse)
async def create_product_route(
    request: Request,
    name: str = Form(...),
    product_id: str = Form(...),
    available_stocks: int = Form(...),
    price: float = Form(...),
    tax_percentage: float = Form(...),
    db: Session = Depends(get_db)
):
    errors = {}
    if crud.get_product_by_name(db, name):
        errors["name"] = "Product with this name already exists."
    if crud.get_product_by_product_id_str(db, product_id):
        errors["product_id"] = "Product with this Product ID already exists."

    if errors:
        return templates.TemplateResponse("add_product.html", {"request": request, "errors": errors,
                                                                "name": name, "product_id": product_id,
                                                                "available_stocks": available_stocks,
                                                                "price": price, "tax_percentage": tax_percentage})

    try:
        product_schema = schemas.ProductCreate(
            name=name, product_id=product_id, available_stocks=available_stocks,
            price=price, tax_percentage=tax_percentage
        )
        crud.create_product(db, product_schema)
        return RedirectResponse(url="/products/", status_code=303)
    except Exception as e:
        errors["general"] = f"An error occurred: {e}"
        return templates.TemplateResponse("add_product.html", {"request": request, "errors": errors,
                                                                "name": name, "product_id": product_id,
                                                                "available_stocks": available_stocks,
                                                                "price": price, "tax_percentage": tax_percentage})

@app.get("/products/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_form(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse("add_product.html", {"request": request, "product": product, "errors": {}})

@app.post("/products/edit/{product_id}", response_class=HTMLResponse)
async def update_product_route(
    request: Request,
    product_id: int,
    name: str = Form(...),
    product_id_str: str = Form(..., alias="product_id"), # Renamed to avoid conflict with path param
    available_stocks: int = Form(...),
    price: float = Form(...),
    tax_percentage: float = Form(...),
    db: Session = Depends(get_db)
):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    errors = {}
    if name != product.name and crud.get_product_by_name(db, name):
        errors["name"] = "Product with this name already exists."
    if product_id_str != product.product_id and crud.get_product_by_product_id_str(db, product_id_str):
        errors["product_id"] = "Product with this Product ID already exists."

    if errors:
        return templates.TemplateResponse("add_product.html", {"request": request, "errors": errors, "product": product,
                                                                "name": name, "product_id": product_id_str, # Use product_id_str here
                                                                "available_stocks": available_stocks,
                                                                "price": price, "tax_percentage": tax_percentage})
    try:
        product_schema = schemas.ProductCreate(
            name=name, product_id=product_id_str, available_stocks=available_stocks,
            price=price, tax_percentage=tax_percentage
        )
        crud.update_product(db, product_id, product_schema)
        return RedirectResponse(url="/products/", status_code=303)
    except Exception as e:
        errors["general"] = f"An error occurred: {e}"
        return templates.TemplateResponse("add_product.html", {"request": request, "errors": errors, "product": product,
                                                                "name": name, "product_id": product_id_str,
                                                                "available_stocks": available_stocks,
                                                                "price": price, "tax_percentage": tax_percentage})


@app.post("/products/delete/{product_id}", response_class=HTMLResponse)
async def delete_product_route(product_id: int, db: Session = Depends(get_db)):
    crud.delete_product(db, product_id)
    return RedirectResponse(url="/products/", status_code=303)

# --- Billing Page (Page 1) ---

@app.get("/billing/", response_class=HTMLResponse)
async def billing_page(request: Request, db: Session = Depends(get_db)):
    products = crud.get_products(db) # To display product IDs
    return templates.TemplateResponse("billing.html", {"request": request, "products": products, "denominations": DENOMINATIONS, "errors": {}})

@app.post("/generate_bill/", response_class=HTMLResponse)
async def generate_bill(
    request: Request,
    background_tasks: BackgroundTasks,
    customer_email: str = Form(...),
    product_ids: List[str] = Form(..., alias="product_id"), # Renamed alias to avoid conflict
    quantities: List[int] = Form(...),
    paid_amount: float = Form(...),
    db: Session = Depends(get_db)
):
    errors = {}
    items_to_purchase = []
    total_bill_amount = 0.0
    total_tax_amount = 0.0

    # Validate inputs
    if not customer_email:
        errors["customer_email"] = "Customer email is required."
    if not product_ids or not quantities:
        errors["products"] = "At least one product must be added."
    if len(product_ids) != len(quantities):
        errors["products"] = "Mismatch in product IDs and quantities."
    if paid_amount <= 0:
        errors["paid_amount"] = "Paid amount must be positive."

    detailed_items = []

    for i in range(len(product_ids)):
        prod_id_str = product_ids[i]
        qty = quantities[i]

        product = crud.get_product_by_product_id_str(db, prod_id_str)
        if not product:
            errors[f"product_{i}"] = f"Product with ID '{prod_id_str}' not found."
            continue
        if qty <= 0:
            errors[f"quantity_{i}"] = f"Quantity for {product.name} must be positive."
            continue
        if product.available_stocks < qty:
            errors[f"stock_{i}"] = f"Not enough stock for {product.name}. Available: {product.available_stocks}, Requested: {qty}"
            continue

        item_price_before_tax = product.price * qty
        item_tax = item_price_before_tax * (product.tax_percentage / 100)
        item_total_price = item_price_before_tax + item_tax

        total_bill_amount += item_total_price
        total_tax_amount += item_tax

        items_to_purchase.append(schemas.PurchaseItemCreate(product_id=product.id, quantity=qty))
        detailed_items.append({
            "product_name": product.name,
            "product_id": product.product_id,
            "quantity": qty,
            "unit_price": product.price,
            "tax_percentage": product.tax_percentage,
            "item_price_before_tax": round(item_price_before_tax, 2),
            "item_tax": round(item_tax, 2),
            "item_total_price": round(item_total_price, 2)
        })

    if errors:
        products = crud.get_products(db)
        return templates.TemplateResponse("billing.html", {"request": request, "products": products, "denominations": DENOMINATIONS, "errors": errors,
                                                            "customer_email": customer_email, "old_product_ids": product_ids, "old_quantities": quantities,
                                                            "paid_amount": paid_amount})

    # Get or create customer
    customer = crud.get_customer_by_email(db, customer_email)
    if not customer:
        customer = crud.create_customer(db, customer_email)

    # Calculate balance
    balance_to_return = paid_amount - total_bill_amount
    if balance_to_return < 0:
        errors["paid_amount"] = f"Paid amount is less than total bill. Remaining: {abs(balance_to_return):.2f}"
        products = crud.get_products(db)
        return templates.TemplateResponse("billing.html", {"request": request, "products": products, "denominations": DENOMINATIONS, "errors": errors,
                                                            "customer_email": customer_email, "old_product_ids": product_ids, "old_quantities": quantities,
                                                            "paid_amount": paid_amount})


    # Create purchase record
    try:
        purchase = crud.create_purchase(db, customer.id, total_bill_amount, paid_amount, items_to_purchase)
    except Exception as e:
        errors["general"] = f"Failed to record purchase: {e}"
        products = crud.get_products(db)
        return templates.TemplateResponse("billing.html", {"request": request, "products": products, "denominations": DENOMINATIONS, "errors": errors,
                                                            "customer_email": customer_email, "old_product_ids": product_ids, "old_quantities": quantities,
                                                            "paid_amount": paid_amount})

    # Calculate change denominations
    change_breakdown = calculate_change_denominations(balance_to_return, DENOMINATIONS)

    # Prepare invoice details for email
    invoice_html = templates.TemplateResponse(
        "bill_details_email.html",
        {
            "request": request, # This is not used in the email template but required by TemplateResponse
            "customer_email": customer_email,
            "purchase_id": purchase.id,
            "detailed_items": detailed_items,
            "total_bill_amount": round(total_bill_amount, 2),
            "total_tax_amount": round(total_tax_amount, 2),
            "paid_amount": round(paid_amount, 2),
            "balance_to_return": round(balance_to_return, 2),
            "change_breakdown": change_breakdown,
            "purchase_time": purchase.purchase_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    ).body.decode("utf-8") # Get the rendered HTML content

    # Send email in background
    background_tasks.add_task(send_invoice_email, customer_email, invoice_html)

    # Render bill details page
    return templates.TemplateResponse(
        "bill_details.html",
        {
            "request": request,
            "customer_email": customer_email,
            "purchase_id": purchase.id,
            "detailed_items": detailed_items,
            "total_bill_amount": round(total_bill_amount, 2),
            "total_tax_amount": round(total_tax_amount, 2),
            "paid_amount": round(paid_amount, 2),
            "balance_to_return": round(balance_to_return, 2),
            "change_breakdown": change_breakdown,
            "purchase_time": purchase.purchase_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

# --- View Previous Purchases ---

@app.get("/customer_purchases/", response_class=HTMLResponse)
async def get_customer_purchases_page(request: Request):
    return templates.TemplateResponse("customer_purchases.html", {"request": request, "customer_email": "", "purchases": [], "errors": {}})

@app.post("/customer_purchases/", response_class=HTMLResponse)
async def post_customer_purchases_page(
    request: Request,
    customer_email: str = Form(...),
    db: Session = Depends(get_db)
):
    errors = {}
    customer = crud.get_customer_by_email(db, customer_email)
    if not customer:
        errors["customer_email"] = "No customer found with this email."
        return templates.TemplateResponse("customer_purchases.html", {"request": request, "customer_email": customer_email, "purchases": [], "errors": errors})

    purchases = crud.get_customer_purchases(db, customer.id)
    return templates.TemplateResponse("customer_purchases.html", {"request": request, "customer_email": customer_email, "purchases": purchases, "errors": {}})

@app.get("/purchase_details/{purchase_id}", response_class=HTMLResponse)
async def view_purchase_details(request: Request, purchase_id: int, db: Session = Depends(get_db)):
    purchase = crud.get_purchase_details(db, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    detailed_items = []
    total_tax_amount = 0.0
    for item in purchase.items:
        item_price_before_tax = item.price_at_purchase * item.quantity
        item_tax = item_price_before_tax * (item.tax_percentage_at_purchase / 100)
        item_total_price = item_price_before_tax + item_tax
        total_tax_amount += item_tax

        detailed_items.append({
            "product_name": item.product.name,
            "product_id": item.product.product_id,
            "quantity": item.quantity,
            "unit_price": item.price_at_purchase,
            "tax_percentage": item.tax_percentage_at_purchase,
            "item_price_before_tax": round(item_price_before_tax, 2),
            "item_tax": round(item_tax, 2),
            "item_total_price": round(item_total_price, 2)
        })

    balance_to_return = purchase.paid_amount - purchase.total_amount
    change_breakdown = calculate_change_denominations(balance_to_return, DENOMINATIONS)


    return templates.TemplateResponse(
        "bill_details.html",
        {
            "request": request,
            "customer_email": purchase.customer.email,
            "purchase_id": purchase.id,
            "detailed_items": detailed_items,
            "total_bill_amount": round(purchase.total_amount, 2),
            "total_tax_amount": round(total_tax_amount, 2),
            "paid_amount": round(purchase.paid_amount, 2),
            "balance_to_return": round(balance_to_return, 2),
            "change_breakdown": change_breakdown,
            "purchase_time": purchase.purchase_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )