import argparse
from src.xai_ids.recent_data import prepare

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["GeNIS2025", "Gotham2025"])
    parser.add_argument("--cap", type=int, default=10000)
    args = parser.parse_args()
    for name in args.datasets:
        prepare(name, args.cap)
