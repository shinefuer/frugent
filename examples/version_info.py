"""Print local package metadata without network access."""

from frugent import __version__


def main() -> None:
    print(f"frugent {__version__}: offline synthetic runtime mechanics")


if __name__ == "__main__":
    main()
