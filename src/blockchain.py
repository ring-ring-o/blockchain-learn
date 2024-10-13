import hashlib
import logging
import sys
import time

from ecdsa import NIST256p, VerifyingKey

from models import Block, Transaction

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

MINING_DIFFICLTY = 3
MINING_SENDER = "THE BLOCKCHAIN"
MINING_REWORD = 1.0


class BlockChain:
    transaction_pool: list
    chain: list[Block]
    blockchain_address: str
    port: str

    def __init__(self, blockchain_address: str = None, port: str = None) -> None:
        self.transaction_pool = []
        self.chain = []
        empty_block = Block(
            timestamp=0.0,
            transactions=[],
            nonce=0,
            previous_hash="",
        )
        self.create_block(0, self.hash(empty_block))
        self.blockchain_address = blockchain_address
        self.port = port

    def create_block(self, nonce: int, previous_hash: str) -> Block:
        block = Block(
            timestamp=time.time(),
            transactions=self.transaction_pool,
            nonce=nonce,
            previous_hash=previous_hash,
        )
        self.chain.append(block)
        self.transaction_pool = []
        return block

    def hash(self, block: Block) -> str:
        sorted_block = block.model_dump_json()
        return hashlib.sha256(sorted_block.encode()).hexdigest()

    def add_transaction(
        self,
        transaction: Transaction,
        sender_public_key: str = None,
        signature: str = None,
    ) -> bool:
        if transaction.sender_blockchain_address == MINING_SENDER:
            self.transaction_pool.append(transaction)
            return True

        if self.verify_transaction_signature(
            sender_public_key=sender_public_key,
            signature=signature,
            transaction=transaction,
        ):
            # # 送信者が保有している以上の仮想通貨を送信しようとしている場合
            # if (
            #     self.calculate_total_amount(transaction.sender_blockchain_address)
            #     < transaction.value
            # ):
            #     logger.error({"action": "add_transaction", "error": "no_value"})
            #     return False

            self.transaction_pool.append(transaction)
            return True
        return False

    def verify_transaction_signature(
        self, sender_public_key: str, signature: str, transaction: Transaction
    ) -> bool:
        sha256 = hashlib.sha256()
        sha256.update(str(transaction).encode("utf-8"))
        message = sha256.digest()
        signature_bytes = bytes().fromhex(signature)
        verifying_key = VerifyingKey.from_string(
            bytes().fromhex(sender_public_key), curve=NIST256p
        )
        verified_key = verifying_key.verify(signature_bytes, message)
        return verified_key

    def valid_proof(
        self,
        transactions: list[Transaction],
        previous_hash: str,
        nonce: float,
        difficulty: int = MINING_DIFFICLTY,
    ) -> bool:
        guess_block = Block(
            timestamp=0.0,
            transactions=transactions,
            nonce=nonce,
            previous_hash=previous_hash,
        )
        guess_hash = self.hash(guess_block)
        return guess_hash[:difficulty] == "0" * difficulty

    def proof_of_work(self) -> int:
        transactions = self.transaction_pool.copy()
        previous_hash = self.hash(self.chain[-1])
        nonce = 0

        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
        return nonce

    def mining(self) -> bool:
        self.add_transaction(
            transaction=Transaction(
                sender_blockchain_address=MINING_SENDER,
                recipient_blockchain_address=self.blockchain_address,
                value=MINING_REWORD,
            )
        )
        nonce = self.proof_of_work()
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)

        logger.info({"action": "mining", "status": "success"})
        return True

    def calculate_total_amount(self, blockchain_address: str) -> float:
        total_amount = 0.0
        for block in self.chain:
            for transaction in block.transactions:
                value = transaction.value
                if blockchain_address == transaction.recipient_blockchain_address:
                    total_amount += value
                if blockchain_address == transaction.sender_blockchain_address:
                    total_amount -= value

        return total_amount
