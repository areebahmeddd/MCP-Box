from pydantic import BaseModel, EmailStr


# Core Entities
class Repository(BaseModel):
    """Git repository information"""

    type: str
    url: str


class Pricing(BaseModel):
    """Pricing information for MCP servers"""

    currency: str
    amount: float


class ToolInfo(BaseModel):
    """MCP tool discovery information"""

    count: int
    names: list[str]


class Meta(BaseModel):
    """Metadata timestamps"""

    created_at: str
    updated_at: str


class MCPServer(BaseModel):
    """Complete MCP Server definition"""

    name: str
    version: str
    description: str
    author: str
    lang: str
    license: str
    entrypoint: str
    repository: Repository
    pricing: Pricing | None = None
    tools: dict | None = None
    security_report: dict | None = None
    meta: Meta | None = None


# Server API Models
class CreateServerRequest(BaseModel):
    """Request payload for creating an MCP server"""

    name: str
    version: str
    description: str
    author: str
    lang: str
    license: str
    entrypoint: str
    repository: Repository
    pricing: Pricing
    tools: dict | None = None


class UpdateServerRequest(BaseModel):
    """Request payload for updating an MCP server"""

    name: str | None = None
    version: str | None = None
    description: str | None = None
    author: str | None = None
    lang: str | None = None
    license: str | None = None
    entrypoint: str | None = None
    repository: Repository | None = None
    pricing: Pricing | None = None
    tools: dict | None = None
    security_report: dict | None = None


# Auth API Models
class AuthRegisterRequest(BaseModel):
    """Request payload for registering a new user"""

    email: EmailStr
    password: str
    display_name: str | None = None


class AuthLoginRequest(BaseModel):
    """Request payload for logging in a user"""

    email: EmailStr
    password: str


class AuthProviderRequest(BaseModel):
    """Request payload for logging in via OAuth providers"""

    provider: str
    id_token: str | None = None
    access_token: str | None = None


class AuthDeviceStartRequest(BaseModel):
    """Request payload to initiate an OAuth device login"""

    provider: str


class AuthDevicePollRequest(BaseModel):
    """Request payload for polling device login status"""

    device_code: str


class AuthRefreshRequest(BaseModel):
    """Request payload for refreshing an ID token"""

    refresh_token: str


class AuthUpdateRequest(BaseModel):
    """Request payload for updating user profile details"""

    display_name: str | None = None
    password: str | None = None


class AuthResponse(BaseModel):
    """Response payload returned after authentication operations"""

    id_token: str
    refresh_token: str
    expires_in: int
    email: str | None = None
    local_id: str | None = None


class AuthUserProfile(BaseModel):
    """Response payload for user profile lookup"""

    email: str | None = None
    local_id: str
    display_name: str | None = None
    email_verified: bool = False
    disabled: bool = False


# Payment API Models
class CreateOrderRequest(BaseModel):
    """Request payload for creating a Razorpay order"""

    server_name: str
    amount: float
    currency: str


class VerifyPaymentRequest(BaseModel):
    """Request payload for verifying a Razorpay payment"""

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    server_name: str
