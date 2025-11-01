from sqlalchemy.orm import Session
import models, schemas
from typing import List

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_product_by_name(db: Session, name: str):
    return db.query(models.Product).filter(models.Product.name == name).first()

def get_product_by_product_id_str(db: Session, product_id_str: str):
    return db.query(models.Product).filter(models.Product.product_id == product_id_str).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product

def get_customer_by_email(db: Session, email: str):
    return db.query(models.Customer).filter(models.Customer.email == email).first()

def create_customer(db: Session, email: str):
    db_customer = models.Customer(email=email)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

def create_purchase(db: Session, customer_id: int, total_amount: float, paid_amount: float, items: List[schemas.PurchaseItemCreate]):
    db_purchase = models.Purchase(
        customer_id=customer_id,
        total_amount=total_amount,
        paid_amount=paid_amount
    )
    db.add(db_purchase)
    db.commit()
    db.refresh(db_purchase)

    for item_data in items:
        product = get_product(db, item_data.product_id)
        if product:
            db_purchase_item = models.PurchaseItem(
                purchase_id=db_purchase.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price_at_purchase=product.price,
                tax_percentage_at_purchase=product.tax_percentage
            )
            db.add(db_purchase_item)
            # Decrease product stocks
            product.available_stocks -= item_data.quantity
    db.commit()
    db.refresh(db_purchase)
    return db_purchase

def get_customer_purchases(db: Session, customer_id: int):
    return db.query(models.Purchase).filter(models.Purchase.customer_id == customer_id).order_by(models.Purchase.purchase_time.desc()).all()

def get_purchase_details(db: Session, purchase_id: int):
    return db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()

def get_recent_purchases(db: Session, limit: int = 10):
    return db.query(models.Purchase)\
             .order_by(models.Purchase.purchase_time.desc())\
             .limit(limit)\
             .all()