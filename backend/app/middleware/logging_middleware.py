import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.time()
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else "unknown"
        
        logger.info(f"Incoming request request_id={request_id} method={method} path={path} client={client_host}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(f"Completed request request_id={request_id} status={response.status_code} duration_ms={process_time:.2f}")
            return response
        except Exception:
            process_time = (time.time() - start_time) * 1000
            logger.exception(f"Failed request request_id={request_id} duration_ms={process_time:.2f}")
            raise
