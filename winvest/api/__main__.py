import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from winvest.api import (
    authorization_route,
    history_route,
    operations_route,
    portfolio_route,
    prediction_route,
    stock_route,
)


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router=authorization_route.router)
    app.include_router(router=operations_route.router, prefix='/operations')
    app.include_router(router=stock_route.router, prefix='/stocks')
    app.include_router(router=history_route.router, prefix='/history')
    app.include_router(router=portfolio_route.router, prefix='/portfolio')
    app.include_router(router=prediction_route.router, prefix='/predict')

    origins = ['http://localhost:3000']

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST'],
        allow_headers=['*'],
    )

    return app


if __name__ == '__main__':
    uvicorn.run(create_app(), host='0.0.0.0')
