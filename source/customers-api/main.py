from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from database import get_connection, ENCRYPTION_KEY

app = FastAPI(title="Customers API - Café Boreal")


class Customer(BaseModel):
    name: str
    email: EmailStr
    identity_number: str  # se recibe en claro desde el cliente/UI, se cifra al guardar


class CustomerOut(BaseModel):
    id: int
    name: str
    email: str
    identity_number: str  # se devuelve descifrado (en claro) para la UI/API


@app.get("/api/customers/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/customers", response_model=List[CustomerOut])
def list_customers():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # pgp_sym_decrypt descifra el campo identity_number al vuelo usando la clave del Secret
            cur.execute(
                """SELECT id, name, email,
                          pgp_sym_decrypt(identity_number, %s) AS identity_number
                   FROM customers ORDER BY id""",
                (ENCRYPTION_KEY,)
            )
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/api/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, email,
                          pgp_sym_decrypt(identity_number, %s) AS identity_number
                   FROM customers WHERE id = %s""",
                (ENCRYPTION_KEY, customer_id)
            )
            customer = cur.fetchone()
            if not customer:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            return customer
    finally:
        conn.close()


@app.post("/api/customers", response_model=CustomerOut, status_code=201)
def create_customer(customer: Customer):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # pgp_sym_encrypt cifra el número de identidad antes de guardarlo en BYTEA
            cur.execute(
                """INSERT INTO customers (name, email, identity_number)
                   VALUES (%s, %s, pgp_sym_encrypt(%s, %s))
                   RETURNING id, name, email""",
                (customer.name, customer.email, customer.identity_number, ENCRYPTION_KEY)
            )
            new_customer = cur.fetchone()
            conn.commit()
            new_customer["identity_number"] = customer.identity_number
            return new_customer
    finally:
        conn.close()


@app.put("/api/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, customer: Customer):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE customers SET name=%s, email=%s, identity_number=pgp_sym_encrypt(%s, %s)
                   WHERE id=%s
                   RETURNING id, name, email""",
                (customer.name, customer.email, customer.identity_number, ENCRYPTION_KEY, customer_id)
            )
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            conn.commit()
            updated["identity_number"] = customer.identity_number
            return updated
    finally:
        conn.close()


@app.delete("/api/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            conn.commit()
    finally:
        conn.close()
            