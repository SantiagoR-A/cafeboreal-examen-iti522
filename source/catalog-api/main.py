from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_connection

app = FastAPI(title="Catalog API - Café Boreal")


class Product(BaseModel):
    name: str
    price: float
    stock: int
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductOut(Product):
    id: int


@app.get("/api/catalog/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/catalog", response_model=list[ProductOut])
def list_products():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, stock, description, image_url FROM products ORDER BY id")
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/api/catalog/{product_id}", response_model=ProductOut)
def get_product(product_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, stock, description, image_url FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            if not product:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            return product
    finally:
        conn.close()


@app.post("/api/catalog", response_model=ProductOut, status_code=201)
def create_product(product: Product):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO products (name, price, stock, description, image_url)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id, name, price, stock, description, image_url""",
                (product.name, product.price, product.stock, product.description, product.image_url)
            )
            new_product = cur.fetchone()
            conn.commit()
            return new_product
    finally:
        conn.close()


@app.put("/api/catalog/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product: Product):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE products SET name=%s, price=%s, stock=%s, description=%s, image_url=%s
                   WHERE id=%s
                   RETURNING id, name, price, stock, description, image_url""",
                (product.name, product.price, product.stock, product.description, product.image_url, product_id)
            )
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            conn.commit()
            return updated
    finally:
        conn.close()


@app.delete("/api/catalog/{product_id}", status_code=204)
def delete_product(product_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            conn.commit()
    finally:
        conn.close()
        