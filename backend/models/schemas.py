from pydantic import BaseModel, Field, EmailStr, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> Any:
        return handler(core_schema.str_schema())

class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr = Field(...)
    name: str = Field(...)
    hashed_password: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Transaction(BaseModel):
    coin_id: str
    quantity: float
    purchase_price: float
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

class Portfolio(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: PyObjectId = Field(...)
    name: str = Field(default="My Portfolio")
    description: Optional[str] = None
    assets: List[Transaction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class MarketData(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    coin_id: str = Field(..., index=True)
    price: float
    market_cap: float
    total_volume: float
    change_24h: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: PyObjectId = Field(...)
    coin_id: str
    alert_type: str  # price_above, price_below, volatility_high
    threshold: float
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Cryptocurrency(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    coin_id: str = Field(..., unique=True)
    symbol: str
    name: str
    image: Optional[str] = None
    description: Optional[str] = None
