import uvicorn
import uvicorn.protocols
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from blockchain import BlockChain
from models import BlockChainCache, PostTransactionRequest, Transaction
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


@app.get("/get_transactions")
def get_transaction():
    block_chain = get_blockchain()
    transactions = block_chain.transaction_pool
    response = {"transactions": transactions, "length": len(transactions)}
    return response


@app.post("/post_transactions")
def post_transactions(body: PostTransactionRequest):
    block_chain = get_blockchain()

    is_created = block_chain.create_transaction(
        transaction=Transaction(
            sender_blockchain_address=body.sender_blockchain_address,
            recipient_blockchain_address=body.recipient_blockchain_address,
            value=body.value,
        ),
        sender_public_key=body.sender_public_key,
        signature=body.signature,
    )

    if not is_created:
        return JSONResponse(
            {"message": "fail"}, status_code=status.HTTP_400_BAD_REQUEST
        )

    return JSONResponse({"message": "success"}, status_code=status.HTTP_201_CREATED)


@app.post("update_transaction")
def update_transaction(body: PostTransactionRequest):
    block_chain = get_blockchain()

    is_updated = block_chain.add_transaction(
        transaction=Transaction(
            sender_blockchain_address=body.sender_blockchain_address,
            recipient_blockchain_address=body.recipient_blockchain_address,
            value=body.value,
        ),
        sender_public_key=body.sender_public_key,
        signature=body.signature,
    )

    if not is_updated:
        return JSONResponse(
            {"message": "fail"}, status_code=status.HTTP_400_BAD_REQUEST
        )

    return JSONResponse({"message": "success"}, status_code=status.HTTP_200_OK)


@app.delete("/delete_transaction")
def delete_transaction():
    block_chain = get_blockchain()
    block_chain.transaction_pool = []

    return {"message": "success"}


@app.post("/mine")
def mine() -> JSONResponse:
    block_chain = get_blockchain()
    is_mined = block_chain.mining()
    if is_mined:
        return {"message": "success"}

    return JSONResponse({"message": "fail"}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/mine/start")
def start_mine():
    get_blockchain().start_mining()
    return {"message": "success"}


@app.post("/consensus")
def consensus():
    block_chain = get_blockchain()
    replaced = block_chain.resolve_conflicts()
    return {"replaced": replaced}


@app.get("/amount")
def get_total_amount(blockchain_address: str):
    return {"amount": get_blockchain().calculate_total_amount(blockchain_address)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="5000", type=str)

    args = parser.parse_args()
    port = args.port

    app.state.port = port

    get_blockchain().run()
    uvicorn.run(app, host="0.0.0.0", port=int(port))
