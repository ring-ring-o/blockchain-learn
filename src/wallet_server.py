import urllib
import urllib.parse

import requests
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from models import PostTransactionRequest, PostWalletTransactionRequest, Transaction
from wallet import Singature, Wallet

app = FastAPI()
app.state.gateway = 8080
temppates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return temppates.TemplateResponse(request=request, name="index.html")


@app.post("/wallet")
def create_wallet():
    my_wallet = Wallet()
    return {
        "private_key": my_wallet.private_key,
        "public_key": my_wallet.public_key,
        "blockchain_address": my_wallet.blockchain_address,
    }


@app.post("/transactions")
def create_transactions(body: PostWalletTransactionRequest):
    signature = Singature(
        sender_private_key=body.sender_private_key,
        sender_public_key=body.sender_public_key,
        transaction=Transaction(
            sender_blockchain_address=body.sender_blockchain_address,
            recipient_blockchain_address=body.recipient_blockchain_address,
            value=body.value,
        ),
    )

    api_body = PostTransactionRequest(
        sender_blockchain_address=body.sender_blockchain_address,
        recipient_blockchain_address=body.recipient_blockchain_address,
        value=body.value,
        sender_public_key=body.sender_public_key,
        signature=signature.generate_signature(),
    )
    response = requests.post(
        urllib.parse.urljoin(app.state.gateway, "/post_transactions"),
        json=api_body.model_dump(),
        timeout=10,
    )

    if response.status_code == status.HTTP_201_CREATED:
        return JSONResponse({"message": "success"}, status_code=status.HTTP_201_CREATED)

    return JSONResponse(
        {"message": "fail", "response": response.text},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


app.get("/wallet/amount")


def calcutate_amount(blockchain_address: str):
    my_blockchain_address = blockchain_address
    response = requests.get(
        urllib.parse.urljoin(app.state.config, "amount"),
        {"blockchain_address": my_blockchain_address},
        timeout=3,
    )

    if response.status_code == 200:
        total = response.json()["amount"]
        return {"message": "success", "amount": total}

    return JSONResponse(
        {"message": "fail", "error": response.content},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


if __name__ == "__main__":
    from argparse import ArgumentParser

    import uvicorn

    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-g", "--gateway", type=str, default="http://127.0.0.1:5000")

    args = parser.parse_args()
    app.state.gateway = args.gateway
    port = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)
