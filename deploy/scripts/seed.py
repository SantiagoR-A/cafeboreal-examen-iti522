"""
Script de seed reproducible - Café Boreal S.R.L.
Genera >=50 productos y >=10 clientes (identidad cifrada con pgcrypto).

Uso:
    DB_HOST=localhost DB_PASSWORD=postgres ENCRYPTION_KEY=miclave python seed.py
"""
import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "cafeboreal")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "clave-de-desarrollo-cambiar-en-produccion")

CATEGORIES = ["Café", "Té", "Pastelería", "Sandwich", "Bebida fría", "Snack"]
BASE_NAMES = [
    "Espresso", "Americano", "Latte", "Capuchino", "Mocha", "Cold Brew",
    "Té Verde", "Té Negro", "Té de Manzanilla", "Chai Latte",
    "Croissant", "Muffin de Arándanos", "Brownie", "Cheesecake", "Galleta de Avena",
    "Sandwich de Jamón", "Sandwich Vegetariano", "Wrap de Pollo", "Bagel",
    "Limonada", "Frappé de Caramelo", "Smoothie de Fresa", "Jugo Natural",
    "Papas Fritas", "Nachos", "Barra de Granola", "Yogurt con Granola"
]


def generate_products(n=55):
    products = []
    for i in range(n):
        base = BASE_NAMES[i % len(BASE_NAMES)]
        category = CATEGORIES[i % len(CATEGORIES)]
        suffix = f" #{i // len(BASE_NAMES) + 1}" if i >= len(BASE_NAMES) else ""
        name = f"{base}{suffix}"
        price = round(2.5 + (i % 12) * 1.35, 2)
        stock = 15 + (i % 10) * 5
        description = f"{base} de la categoría {category}, preparado en Café Boreal."
        products.append((name, price, stock, description, None))
    return products


def generate_customers(n=12):
    customers = []
    for i in range(1, n + 1):
        name = f"Cliente Demo {i}"
        email = f"cliente{i}@cafeboreal-demo.com"
        identity_number = f"CB-{1000 + i}-{i:04d}"  # número de identidad ficticio para pruebas
        customers.append((name, email, identity_number))
    return customers


def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        with conn.cursor() as cur:
            products = generate_products()
            for name, price, stock, description, image_url in products:
                cur.execute(
                    """INSERT INTO products (name, price, stock, description, image_url)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (name, price, stock, description, image_url)
                )
            print(f"Insertados {len(products)} productos.")

            customers = generate_customers()
            for name, email, identity_number in customers:
                cur.execute(
                    """INSERT INTO customers (name, email, identity_number)
                       VALUES (%s, %s, pgp_sym_encrypt(%s, %s))
                       ON CONFLICT (email) DO NOTHING""",
                    (name, email, identity_number, ENCRYPTION_KEY)
                )
            print(f"Insertados {len(customers)} clientes (identidad cifrada).")

            conn.commit()
            print("Seed completado exitosamente.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    