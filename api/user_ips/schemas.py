from ipaddress import IPv4Address, IPv6Address
from typing import Optional

from pydantic import BaseModel

IPAddress = IPv4Address | IPv6Address


class UserIpCreateSchema(BaseModel):
    user_id: int
    static_ip: IPAddress
    private_ip: IPAddress


class UserIpUpdateSchema(BaseModel):
    user_id: Optional[int] = None
    static_ip: Optional[IPAddress] = None
    private_ip: Optional[IPAddress] = None
