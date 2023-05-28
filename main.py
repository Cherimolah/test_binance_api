import asyncio
import time
from typing import Literal
import json
import random

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
import uvicorn
from binance import AsyncClient
from binance.exceptions import BinanceOrderException, BinanceAPIException
from pydantic import BaseModel

from config import API_KEY, SECRET_KEY

app = FastAPI()


# Дата-класс модели запроса
class Order(BaseModel):
    volume: float  # Объем в долларах
    number: int  # На сколько ордеров нужно разбить этот объем
    amountDif: float  # Разброс в долларах, в пределах которого случайным образом выбирается объем
    side: Literal["SELL", "BUY"]  # Сторона торговли (SELL или BUY)
    priceMin: float  # Нижний диапазон цены, в пределах которого нужно случайным образом выбрать цену
    priceMax: float  # Верхний диапазон цены, в пределах которого нужно случайным образом выбрать цену


# Функция для создания подключение к Бинанс
async def create_client():
    client = await AsyncClient.create(API_KEY, SECRET_KEY, testnet=True)
    return client


# Основная страница
@app.get("/")
async def root():
    return FileResponse("index.html")


# Функция для создания нового ордера
@app.post("/order")
async def order_new(order: Order):
    client = await create_client()
    # Весь объём разделяется на number стаков ордеров со средним объёмом base_volume
    base_volume = order.volume // order.number
    orders = []
    tasks = []
    for i in range(order.number):  # Проходимся по количеству стаков ордеров
        # Точный объём одного ордера
        volume = round(random.uniform(base_volume - order.number // 2,
                                      base_volume + order.number // 2), 2)
        # Количество ордеров в одном стаке
        count_orders = int(volume // order.priceMax)
        for i1 in range(count_orders):
            # Цена одного ордера в диапазоне от priceMin до priceMax
            price = round(random.uniform(order.priceMin, order.priceMax), 2)
            tasks.append(asyncio.ensure_future(client.create_order(
                symbol='BTCUSDT',
                side=order.side,
                type=client.ORDER_TYPE_MARKET,
                timestamp=time.time(),
                quoteOrderQty=price
            )))
        try:
            # Чтобы было быстрее конкурентно создаём запросы
            responses = await asyncio.gather(*tasks)
        except (BinanceAPIException, BinanceOrderException) as e:
            # Ловим ошибки с запросами
            return PlainTextResponse(json.dumps({
                "error": str(e)
            }))
        orders.append(responses)  # Составляем список с number стаков ордеров
    response = {"orders": orders}
    await client.close_connection()  # Закрываем подключение к Бинанс
    return PlainTextResponse(json.dumps(response, indent=4))


if __name__ == '__main__':
    uvicorn.run(app)  # Запуск веб-сервера
