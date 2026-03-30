from extract import extract
from load import load
from transform import transform


def run() -> None:
    df = extract()
    load(df)
    transform()
    print("[pipeline] complete")


if __name__ == '__main__':
    run()
