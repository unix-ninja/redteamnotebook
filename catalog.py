from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from base import Base

class NodeGraph(Base):
  __tablename__ = "node_graph"
  nodeid = Column(String, primary_key=True)
  parentid = Column(String)
  basename = Column(String)
  icon = Column(String)
  mtime = Column(Float)

class Note(Base):
  __tablename__ = "notes"
  nodeid = Column(String, primary_key=True)
  content = Column(String)
  mtime = Column(Float)
