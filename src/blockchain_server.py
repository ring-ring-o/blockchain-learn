import uvicorn
import uvicorn.protocols
from fastapi import FastAPI

from blockchain import BlockChain
from models import BlockChainCache
from wallet import Wallet

app = FastAPI()
app.state.port = 8000
cache = BlockChainCache()


def get_blockchain() -> BlockChain:
    cached_blockchain = cache.blockchain
    if not cached_blockchain:
        miners_wallet = Wallet()
        cache.blockchain = BlockChain(
            blockchain_address=miners_wallet.blockchain_address,
            port=app.state.port,
        )

    return cache.blockchain


@app.get("/")
def check_connect():
    return {"connection": True}


@app.get("/chain")
def get_chain():
    block_chain = get_blockchain()
    response = {"chain": block_chain.chain}
    return response


def transaction():
    pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="5000", type=str)

    args = parser.parse_args()
    port = args.port

    app.state.port = port
    uvicorn.run(app, host="0.0.0.0", port=int(port))
