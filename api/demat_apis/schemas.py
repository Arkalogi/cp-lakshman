from typing import Optional

from pydantic import BaseModel, model_validator

from api.commons import enums


class DematApiConfigSchema(BaseModel):
    api_provider: enums.ApiProvider
    demat_provider: enums.DematProvider

    @model_validator(mode="after")
    def validate_provider_pair(self):
        if (
            self.demat_provider == enums.DematProvider.ZERODHA
            and self.api_provider != enums.ApiProvider.KITE
        ):
            raise ValueError("ZERODHA must use KITE api_provider")
        if (
            self.demat_provider == enums.DematProvider.FINVASIA
            and self.api_provider != enums.ApiProvider.SHOONYA
        ):
            raise ValueError("FINVASIA must use SHOONYA api_provider")
        return self


class DematApiCreateSchema(BaseModel):
    config: DematApiConfigSchema
    user_id: int = None


class DematApiUpdateSchema(BaseModel):
    config: Optional[DematApiConfigSchema] = None
    user_id: Optional[int] = None
