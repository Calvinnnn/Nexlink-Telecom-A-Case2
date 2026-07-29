from pydantic import BaseModel, Field, ConfigDict

#this file will contain all the schemas for the API endpoints, we should add more ofc

class AccountVerificationSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    account_id: int = Field(..., description="The numeric account ID", gt=0)
    #enforce regex pattern for 4-digit PIN, allowing leading zeros
    pin: str = Field(..., description="The 4-digit security PIN (supports leading zeros)", pattern=r"^\d{4}$")