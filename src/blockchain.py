import contextlib
import hashlib
import logging
import sys
import threading
import time

import requests
from ecdsa import NIST256p, VerifyingKey

from models import Block, Transaction
from utils import find_neighbours, get_host

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

MINING_DIFFICLTY = 3
MINING_SENDER = "THE BLOCKCHAIN"
MINING_REWORD = 1.0
MINING_TIMER_SEC = 20

BLOCKCHAIN_PORT_RANGE = (5000, 5003)
NEIGHBOURS_IP_RANGE_NUM = (0, 1)
BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC = 20


class BlockChain:
    transaction_pool: list
    chain: list[Block]
    blockchain_address: str
    port: str
    mining_semaphore: threading.Semaphore
    neighbours: list
    sync_neighbours_semaphore: threading.Semaphore

    def __init__(self, blockchain_address: str = None, port: str = None) -> None:
        self.transaction_pool = []
        self.chain = []
        empty_block = Block(
            timestamp=0.0,
            transactions=[],
            nonce=0,
            previous_hash="",
        )
        self.neighbours = []
        self.create_block(0, self.hash(empty_block))
        self.blockchain_address = blockchain_address
        self.port = port
        self.mining_semaphore = threading.Semaphore(1)
        self.sync_neighbours_semaphore = threading.Semaphore(1)

    def run(self):
        self.sync_neighbours()
        self.resolve_conflicts()
        self.start_mining()

    def set_neighbours(self):
        self.neighbours = find_neighbours(
            my_host=get_host(),
            my_port=self.port,
            start_ip_range=NEIGHBOURS_IP_RANGE_NUM[0],
            end_ip_range=NEIGHBOURS_IP_RANGE_NUM[1],
            start_port=BLOCKCHAIN_PORT_RANGE[0],
            end_port=BLOCKCHAIN_PORT_RANGE[1],
        )
        logger.info({"action": "set_neighours", "neighbours": self.neighbours})

    def sync_neighbours(self):
        is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.sync_neighbours_semaphore.release)
                self.set_neighbours()
                loop = threading.Timer(
                    BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC, self.sync_neighbours
                )
                loop.start()

    def create_block(self, nonce: int, previous_hash: str) -> Block:
        block = Block(
            timestamp=time.time(),
            transactions=self.transaction_pool,
            nonce=nonce,
            previous_hash=previous_hash,
        )
        self.chain.append(block)
        self.transaction_pool = []

        for node in self.neighbours:
            requests.delete(f"http://{node}/delete_transaction")
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
            if (
                self.calculate_total_amount(transaction.sender_blockchain_address)
                < transaction.value
            ):
                logger.error({"action": "add_transaction", "error": "no_value"})
                return False

            self.transaction_pool.append(transaction)
            return True
        return False

    def create_transaction(
        self,
        transaction: Transaction,
        sender_public_key: str,
        signature: str,
    ) -> bool:
        is_transactions = self.add_transaction(
            transaction, sender_public_key, signature
        )

        if is_transactions:
            for node in self.neighbours:
                requests.post(
                    f"http://{node}/update_transactions",
                    json={
                        "sender_blockchain_address": transaction.sender_blockchain_address,
                        "recipient_blockchain_address": transaction.recipient_blockchain_address,
                        "value": transaction.value,
                        "sender_public_key": sender_public_key,
                        "signature": signature,
                    },
                )
        return is_transactions

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
        # if not self.transaction_pool:
        #     return False

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

        for node in self.neighbours:
            requests.post(f"http://{node}/consensus")
        return True

    def start_mining(self) -> None:
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining()
                loop = threading.Timer(MINING_TIMER_SEC, self.start_mining)
                loop.start()

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

    def valid_blockchain(self, chain: list[Block]) -> bool:
        pre_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block["previous_hash"] != self.hash(pre_block):
                return False

            if not self.valid_proof(
                transactions=block.transactions,
                previous_hash=block.previous_hash,
                nonce=block.nonce,
                difficulty=MINING_DIFFICLTY,
            ):
                return False

            pre_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        longest_chain = None
        max_length = len(self.chain)

        for node in self.neighbours:
            response = requests.get(f"http://{node}/chain")
            if response.status_code == 200:
                response_json = response.json()
                chain: list[Block] = response_json["chain"]
                chain_length = len(chain)

                if chain_length > max_length and self.valid_blockchain(chain=chain):
                    max_length = chain_length
                    longest_chain = chain

        if longest_chain:
            self.chain = longest_chain
            logger.info({"action": "resolve)confilixts", "status": "replaced"})
            return True

        logger.info({"action": "resolve)confilixts", "status": "not_replaced"})
        return False
