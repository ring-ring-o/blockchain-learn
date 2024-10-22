from pydantic import BaseModel


class Transaction(BaseModel):
    sender_blockchain_address: str
    recipient_blockchain_address: str
    value: float


class Block(BaseModel):
    timestamp: float
    transactions: list[Transaction]
    nonce: int
    previous_hash: str


class BlockChainCache(BaseModel):
    blockchain: Block | None = None


class PostTransactionRequest(Transaction):
    sender_public_key: str
    signature: str


class PostWalletTransactionRequest(Transaction):
    sender_private_key: str
    sender_public_key: str
