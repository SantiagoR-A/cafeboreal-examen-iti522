from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from database import get_connection

app = FastAPI(title="Orders API - Café Boreal")


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int


class OrderIn(BaseModel):
    customer_id: int
    items: List[OrderItemIn]


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    id: int
    customer_id: int
    total: float
    status: str
    items: List[OrderItemOut]


@app.get("/api/orders/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/orders", response_model=OrderOut, status_code=201)
def create_order(order: OrderIn):
    if not order.items:
        raise HTTPException(status_code=400, detail="El pedido debe tener al menos un item")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar que el cliente existe
            cur.execute("SELECT id FROM customers WHERE id = %s", (order.customer_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Cliente no encontrado")

            total = 0
            items_with_price = []

            # Validar cada producto, tomar su precio actual y calcular el total
            for item in order.items:
                cur.execute("SELECT price, stock FROM products WHERE id = %s", (item.product_id,))
                product = cur.fetchone()
                if not product:
                    raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
                if product["stock"] < item.quantity:
                    raise HTTPException(status_code=400, detail=f"Stock insuficiente para producto {item.product_id}")

                unit_price = float(product["price"])
                total += unit_price * item.quantity
                items_with_price.append((item.product_id, item.quantity, unit_price))

            # Crear el pedido
            cur.execute(
                "INSERT INTO orders (customer_id, total, status) VALUES (%s, %s, 'pending') RETURNING id, customer_id, total, status",
                (order.customer_id, total)
            )
            new_order = cur.fetchone()

            # Insertar los items y descontar stock
            for product_id, quantity, unit_price in items_with_price:
                cur.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                    (new_order["id"], product_id, quantity, unit_price)
                )
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s",
                    (quantity, product_id)
                )

            conn.commit()

            new_order["items"] = [
                {"product_id": p, "quantity": q, "unit_price": up} for p, q, up in items_with_price
            ]
            return new_order
    finally:
        conn.close()


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, customer_id, total, status FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Pedido no encontrado")

            cur.execute(
                "SELECT product_id, quantity, unit_price FROM order_items WHERE order_id = %s",
                (order_id,)
            )
            order["items"] = cur.fetchall()
            return order
    finally:
        conn.close()


@app.get("/api/orders", response_model=List[OrderOut])
def list_orders():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, customer_id, total, status FROM orders ORDER BY id")
            orders = cur.fetchall()
            for order in orders:
                cur.execute(
                    "SELECT product_id, quantity, unit_price FROM order_items WHERE order_id = %s",
                    (order["id"],)
                )
                order["items"] = cur.fetchall()
            return orders
    finally:
        conn.close()
        