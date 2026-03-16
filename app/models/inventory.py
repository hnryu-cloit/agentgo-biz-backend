from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from app.db.database import Base
from datetime import datetime

class ItemMaster(Base):
    __tablename__ = 'item_masters'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    unit = Column(String)
    category = Column(String)
    safety_stock = Column(Float)
    store_id = Column(Integer, ForeignKey('stores.id'))

class InventoryAudit(Base):
    __tablename__ = 'inventory_audits'
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('item_masters.id'))
    store_id = Column(Integer, ForeignKey('stores.id'))
    actual_stock = Column(Float)
    audit_date = Column(DateTime, default=datetime.utcnow)

class TheoreticalInventory(Base):
    __tablename__ = 'theoretical_inventories'
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('item_masters.id'))
    store_id = Column(Integer, ForeignKey('stores.id'))
    theoretical_stock = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)
