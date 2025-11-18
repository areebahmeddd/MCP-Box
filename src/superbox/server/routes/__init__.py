from superbox.server.routes.auth import router as auth_router
from superbox.server.routes.servers import router as servers_router
from superbox.server.routes.payment import router as payment_router

__all__ = ["auth_router", "servers_router", "payment_router"]
