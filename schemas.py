from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    product_id: str
    available_stocks: int
    price: float
    tax_percentage: float

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True

class CustomerBase(BaseModel):
    email: str

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: int
    purchases: List["Purchase"] = []

    class Config:
        orm_mode = True

class PurchaseItemBase(BaseModel):
    product_id: int
    quantity: int

class PurchaseItemCreate(PurchaseItemBase):
    pass

class PurchaseItem(PurchaseItemBase):
    id: int
    price_at_purchase: float
    tax_percentage_at_purchase: float

    class Config:
        orm_mode = True

class PurchaseBase(BaseModel):
    customer_id: int
    total_amount: float
    paid_amount: float

class PurchaseCreate(PurchaseBase):
    items: List[PurchaseItemCreate]

class Purchase(PurchaseBase):
    id: int
    purchase_time: datetime
    items: List[PurchaseItem] = []

    class Config:
        orm_mode = True

# Update forward refs for models that reference each other
Customer.update_forward_refs()
Purchase.update_forward_refs()