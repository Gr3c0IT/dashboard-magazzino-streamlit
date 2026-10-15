import secrets
import string
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = BASE_DIR / "password_output.txt"

def genera_password(length=20):
    minuscole = string.ascii_lowercase
    maiuscole = string.ascii_uppercase
    numeri = string.digits
    simboli = "!@#$%^&*()-_=+[]{}?"

    chars = [
        secrets.choice(minuscole),
        secrets.choice(maiuscole),
        secrets.choice(numeri),
        secrets.choice(simboli),
    ]

    pool = minuscole + maiuscole + numeri + simboli

    while len(chars) < length:
        chars.append(secrets.choice(pool))

    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)

def genera_hash(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def main():
    password = genera_password(20)
    hashed = genera_hash(password)

    output = []
    output.append("PASSWORD:")
    output.append(password)
    output.append("")
    output.append("HASH:")
    output.append(hashed)

    testo = "\n".join(output)
    print(testo)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(testo + "\n")

if __name__ == "__main__":
    main()