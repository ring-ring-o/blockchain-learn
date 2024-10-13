import binascii
import codecs
import hashlib

import base58
from ecdsa import NIST256p, SigningKey, VerifyingKey

from models import Transaction
from utils import pprint


class Wallet:
    _private_key: SigningKey
    _public_key: VerifyingKey
    _blockchain_address: str

    def __init__(self) -> None:
        self._private_key = SigningKey.generate(curve=NIST256p)
        self._public_key = self._private_key.get_verifying_key()
        self._blockchain_address = self.generate_blockchain_address()

    @property
    def private_key(self) -> str:
        return self._private_key.to_string().hex()

    @property
    def public_key(self) -> str:
        key_bytes: bytes = self._public_key.to_string()
        return key_bytes.hex()

    @property
    def blockchain_address(self) -> str:
        return self._blockchain_address

    def generate_blockchain_address(self) -> str:
        # 2.公開鍵をsha256でハッシュ化
        public_key_bytes = self._public_key.to_string()
        sha256_bpk = hashlib.sha256(public_key_bytes)
        sha256_bpk_digest = sha256_bpk.digest()

        # 3.Ripemd160を使用してSHA-256をハッシュか
        ripemd160_bpk = hashlib.new("ripemd160")
        ripemd160_bpk.update(sha256_bpk_digest)
        ripemd160_bpk_digest = ripemd160_bpk.digest()
        ripemd160_bpk_hex = codecs.encode(ripemd160_bpk_digest, "hex")

        # 4.ネットワークバイトを追加
        network_byte = b"00"
        network_bitcoin_public_key = network_byte + ripemd160_bpk_hex
        network_bitcoin_public_key_bytes = codecs.decode(
            network_bitcoin_public_key, "hex"
        )

        # 5.二重にSHA256でハッシュ化
        sha256_bpk = hashlib.sha256(network_bitcoin_public_key_bytes)
        sha256_bpk_digest = sha256_bpk.digest()
        sha256_double_bpk = hashlib.sha256(sha256_bpk_digest)
        sha256_double_bpk_digest = sha256_double_bpk.digest()
        sha256_hex = codecs.encode(sha256_double_bpk_digest, "hex")

        # 6.チェックサムを取得
        checksum = sha256_hex[:8]

        # 7.公開鍵とチェックサムを結合する
        address_hex = (network_bitcoin_public_key + checksum).decode("utf-8")

        # 8.Base58でエンコード
        blockchain_address = base58.b58encode(binascii.unhexlify(address_hex)).decode(
            "utf-8"
        )

        return blockchain_address


class Singature:
    sender_private_key: str
    sender_public_key: str
    transaction: Transaction

    def __init__(
        self,
        sender_private_key: str,
        sender_public_key: str,
        transaction: Transaction,
    ) -> None:
        self.sender_private_key = sender_private_key
        self.sender_public_key = sender_public_key
        self.transaction = transaction

    def generate_signature(self) -> str:
        sha256 = hashlib.sha256()
        sha256.update(str(self.transaction).encode("utf-8"))
        message = sha256.digest()

        private_key = SigningKey.from_string(
            bytes().fromhex(self.sender_private_key), curve=NIST256p
        )
        private_key_sign: bytes = private_key.sign(message)
        signature = private_key_sign.hex()
        return signature


if __name__ == "__main__":
    wallet_M = Wallet()
    wallet_A = Wallet()
    wallet_B = Wallet()

    a_to_B_transaction = Transaction(
        sender_blockchain_address=wallet_A.blockchain_address,
        recipient_blockchain_address=wallet_B.blockchain_address,
        value=1.0,
    )
    s = Singature(
        sender_private_key=wallet_A.private_key,
        sender_public_key=wallet_A.public_key,
        transaction=a_to_B_transaction,
    )

    from blockchain import BlockChain

    block_chain = BlockChain(blockchain_address=wallet_M.blockchain_address)
    is_added = block_chain.add_transaction(
        transaction=Transaction(
            sender_blockchain_address=wallet_A.blockchain_address,
            recipient_blockchain_address=wallet_B.blockchain_address,
            value=1.0,
        ),
        sender_public_key=wallet_A.public_key,
        signature=s.generate_signature(),
    )

    print("added?", is_added)
    block_chain.mining()
    pprint(block_chain.chain)

    print("A", block_chain.calculate_total_amount(wallet_A.blockchain_address))
    print("B", block_chain.calculate_total_amount(wallet_B.blockchain_address))
