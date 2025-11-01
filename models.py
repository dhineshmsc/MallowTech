from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    product_id = Column(String, unique=True, index=True) # Unique product identifier
    available_stocks = Column(Integer, default=0)
    price = Column(Float)
    tax_percentage = Column(Float) # e.g., 5.0 for 5%

    purchase_items = relationship("PurchaseItem", back_populates="product")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)

    purchases = relationship("Purchase", back_populates="customer")

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    total_amount = Column(Float)
    paid_amount = Column(Float)
    purchase_time = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_at_purchase = Column(Float) # Price of one unit at the time of purchase
    tax_percentage_at_purchase = Column(Float) # Tax at the time of purchase

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")