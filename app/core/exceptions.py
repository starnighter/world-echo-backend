from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, code: int, message: str) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


class BadRequestException(AppException):
    def __init__(self, message: str = "request parameter error") -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, 400, message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "unauthorized") -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, 401, message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "forbidden") -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, 403, message)


class NotFoundException(AppException):
    def __init__(self, message: str = "not found") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, 404, message)


class ConflictException(AppException):
    def __init__(self, message: str = "conflict") -> None:
        super().__init__(status.HTTP_409_CONFLICT, 409, message)


class UnprocessableException(AppException):
    def __init__(self, message: str = "unprocessable entity") -> None:
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, 422, message)


class TooManyRequestsException(AppException):
    def __init__(self, message: str = "too many requests") -> None:
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, 429, message)
