from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from wallet import Wallet

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
