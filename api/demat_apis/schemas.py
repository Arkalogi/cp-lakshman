from typing import Optional

from pydantic import BaseModel, model_validator

from api.commons import enums


class DematApiConfigSchema(BaseModel):
    api_provider: enums.ApiProvider = enums.ApiProvider.PAPER
    demat_provider: enums.DematProvider = enums.DematProvider.ARKALOGI
    api_key: Optional[str]
    api_secret: Optional[str]
    mobile_number: Optional[str]
    totp_secret: Optional[str]
    pin: Optional[str]
    redirect_url: Optional[str]

    @model_validator(mode="after")
    def validate_provider_pair(self):
        if (
            self.demat_provider == enums.DematProvider.UPSTOX
            and self.api_provider != enums.ApiProvider.UPSTOX
        ):
            raise ValueError("UPSTOX must use UPSTOX api_provider")
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
        if (
            self.demat_provider == enums.DematProvider.ARKALOGI
            and self.api_provider != enums.ApiProvider.PAPER
        ):
            raise ValueError("ARKALOGI must use PAPER api_provider")
        if (
            self.demat_provider == enums.DematProvider.DEMO
            and self.api_provider != enums.ApiProvider.PAPER
        ):
            raise ValueError("DEMO must use PAPER api_provider")
        if (
            self.demat_provider == enums.DematProvider.ANGELONE
            and self.api_provider != enums.ApiProvider.ANGELONE
        ):
            raise ValueError("ANGELONE must use ANGELONE api_provider")
        if (
            self.demat_provider == enums.DematProvider.GROW
            and self.api_provider != enums.ApiProvider.GROW
        ):
            raise ValueError("GROW must use GROW api_provider")
        return self


class DematApiCreateSchema(BaseModel):
    config: DematApiConfigSchema
    user_id: int = None


class DematApiUpdateSchema(BaseModel):
    config: Optional[DematApiConfigSchema] = None
    user_id: Optional[int] = None
