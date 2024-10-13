from models import Block


def pprint(chains: list[Block]) -> None:
    for index, chain in enumerate(chains):
        print(f"{"="*25} Chain {index} {"="*25}")
        for key, value in chain.model_dump().items():
            print(f"{key:15}{value}")
    print(f"{"*"*25}")
