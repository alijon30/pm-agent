"""Print the Gemini/Gemma model ids visible to this API key."""

from google import genai


def main() -> None:
    client = genai.Client()
    names = sorted(m.name.removeprefix("models/") for m in client.models.list())
    for name in names:
        if name.startswith(("gemini-3", "gemma")):
            print(name)


if __name__ == "__main__":
    main()
