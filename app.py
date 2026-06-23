# -*- coding: utf-8 -*-
import os
import uuid
import datetime
import smtplib
from email.message import EmailMessage

from fastapi import FastAPI, Form, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import (Column, Integer, String, Date, DateTime, Enum,
                        Boolean, ForeignKey, create_engine, func)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ----------------------------------------------------------------------
# Configuration (read from environment)
# ----------------------------------------------------------------------
DATABASE_URL = "sqlite:///./hotel.db"
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 0))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "adminpass")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:10000")

# ----------------------------------------------------------------------
# Database setup
# ----------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    telefono = Column(String, nullable=False)


class Habitacion(Base):
    __tablename__ = "habitaciones"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)
    precio_noche = Column(Integer, nullable=False)
    descripcion = Column(String, nullable=False)
    capacidad = Column(Integer, nullable=False)
    disponibilidad = Column(Boolean, default=True)


class Reserva(Base):
    __tablename__ = "reservas"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    habitacion_id = Column(Integer, ForeignKey("habitaciones.id"), nullable=False)
    fecha_checkin = Column(Date, nullable=False)
    fecha_checkout = Column(Date, nullable=False)
    num_huespedes = Column(Integer, nullable=False)
    solicitudes = Column(String, nullable=True)
    estado = Column(
        Enum("pendiente", "confirmada", "cancelada", name="estado_enum"),
        default="pendiente",
    )
    referencia = Column(String, unique=True, nullable=False)
    fecha_creacion = Column(DateTime, default=func.now())

    cliente = relationship("Cliente")
    habitacion = relationship("Habitacion")


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------------------
app = FastAPI()
security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if (credentials.username != ADMIN_USER) or (credentials.password != ADMIN_PASS):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def send_confirmation_email(to_email: str, nombre: str, referencia: str):
    if not SMTP_SERVER:
        return
    msg = EmailMessage()
    msg["Subject"] = "Reservation Confirmation"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.set_content(
        f"Dear {nombre},\n\nYour reservation has been received.\nReference: {referencia}\n\nThank you."
    )
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        # In production you would log the error
        pass


def generate_reference() -> str:
    return str(uuid.uuid4()).split("-")[0].upper()


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    """Rich home page with hotel description, amenities and gallery."""
    html = """
    <!doctype html>
    <html lang="en">
    <head>
        <title>Hotel Paradise</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {font-family:Arial,Helvetica,sans-serif;background:#FFFFFF;color:#000000;}
            .navbar {background:#003366;}
            .hero {
                background-image: url('https://images.unsplash.com/photo-1501117716987-c8e5b5e1b7c5');
                background-size: cover;
                background-position: center;
                height: 70vh;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#FFFFFF;
                text-align:center;
            }
            .btn-gold {background:#DAA520;color:#FFFFFF;}
            .section-title {color:#003366;margin-top:2rem;margin-bottom:1rem;}
            .gallery img {width:100%;height:auto;border-radius:5px;}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
          <div class="container-fluid">
            <a class="navbar-brand" href="/">Hotel Paradise</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
                    data-bs-target="#navbarNav" aria-controls="navbarNav"
                    aria-expanded="false" aria-label="Toggle navigation">
              <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
              <ul class="navbar-nav ms-auto">
                <li class="nav-item"><a class="nav-link active" href="/">Home</a></li>
                <li class="nav-item"><a class="nav-link" href="/rooms">Rooms</a></li>
                <li class="nav-item"><a class="nav-link" href="/admin">Admin</a></li>
              </ul>
            </div>
          </div>
        </nav>

        <section class="hero">
            <div>
                <h1>Welcome to Hotel Paradise</h1>
                <p>Luxury, comfort and unforgettable experiences.</p>
                <a href="/rooms" class="btn btn-gold btn-lg">Reserve Now</a>
            </div>
        </section>

        <section class="container py-5">
            <h2 class="section-title">About Our Hotel</h2>
            <p>
                Nestled in the heart of the city, Hotel Paradise offers a perfect blend of modern
                elegance and classic hospitality. Our rooms are designed to provide maximum comfort,
                while our facilities include a rooftop pool, a full-service spa, and a gourmet restaurant.
                Whether you are traveling for business or leisure, our dedicated staff will ensure
                a memorable stay.
            </p>
        </section>

        <section class="container py-5">
            <h2 class="section-title">Amenities</h2>
            <ul class="list-group">
                <li class="list-group-item">Free high‑speed Wi‑Fi</li>
                <li class="list-group-item">24‑hour front desk</li>
                <li class="list-group-item">Rooftop swimming pool</li>
                <li class="list-group-item">Full‑service spa</li>
                <li class="list-group-item">Gym & fitness center</li>
                <li class="list-group-item">Restaurant & bar</li>
                <li class="list-group-item">Conference rooms</li>
                <li class="list-group-item">Parking garage</li>
            </ul>
        </section>

        <section class="container py-5">
            <h2 class="section-title">Gallery</h2>
            <div class="row gallery">
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1560185127-6a8c5c5c8c5b" alt="Lobby"></div>
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1582719478250-9c6c5c5c5c5d" alt="Room"></div>
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1556912995-9c5c5c5c5c5e" alt="Pool"></div>
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1522708323590-47c2c5c5c5c5f" alt="Restaurant"></div>
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1542314831-068cd1c5c5c5g" alt="Spa"></div>
                <div class="col-md-4 mb-3"><img src="https://images.unsplash.com/photo-1502672260266-1c1c5c5c5c5h" alt="Gym"></div>
            </div>
        </section>

        <footer class="bg-light py-4">
            <div class="container text-center">
                <p>&copy; 2024 Hotel Paradise. All rights reserved.</p>
                <p>Contact: info@hotelparadise.com | +1 234 567 890</p>
            </div>
        </footer>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/rooms", response_class=HTMLResponse)
def list_rooms(db: SessionLocal = Depends(get_db)):
    rooms = db.query(Habitacion).all()
    cards = ""
    for r in rooms:
        cards += f"""
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <img src="https://via.placeholder.com/400x200?text={r.tipo}" class="card-img-top" alt="{r.tipo}">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">{r.tipo}</h5>
                    <p class="card-text">{r.descripcion}</p>
                    <p class="card-text"><strong>${r.precio_noche} per night</strong></p>
                    <a href="/reserve?room_id={r.id}" class="btn btn-gold mt-auto">Select</a>
                </div>
            </div>
        </div>
        """
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <title>Rooms</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>.btn-gold {{background:#DAA520;color:#fff;}}</style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark" style="background:#003366;">
          <div class="container-fluid">
            <a class="navbar-brand" href="/">Hotel Paradise</a>
            <div class="collapse navbar-collapse">
              <ul class="navbar-nav ms-auto">
                <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
                <li class="nav-item"><a class="nav-link active" href="/rooms">Rooms</a></li>
                <li class="nav-item"><a class="nav-link" href="/admin">Admin</a></li>
              </ul>
            </div>
          </div>
        </nav>
        <div class="container py-4">
            <div class="row">
                {cards}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/reserve", response_class=HTMLResponse)
def reserve_form(room_id: int, db: SessionLocal = Depends(get_db)):
    room = db.query(Habitacion).filter(Habitacion.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <title>Reserve</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>.btn-gold {{background:#DAA520;color:#fff;}}</style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark" style="background:#003366;">
          <div class="container-fluid">
            <a class="navbar-brand" href="/">Hotel Paradise</a>
          </div>
        </nav>
        <div class="container py-4">
            <h2 class="mb-4">Reserve {room.tipo}</h2>
            <form method="post" action="/reserve">
                <input type="hidden" name="room_id" value="{room.id}">
                <div class="mb-3">
                    <label class="form-label">Full Name</label>
                    <input type="text" class="form-control" name="nombre" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-control" name="email" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Phone</label>
                    <input type="text" class="form-control" name="telefono" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Guests</label>
                    <input type="number" class="form-control" name="num_huespedes" min="1" max="{room.capacidad}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Check‑in Date</label>
                    <input type="date" class="form-control" name="fecha_checkin" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Check‑out Date</label>
                    <input type="date" class="form-control" name="fecha_checkout" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Special Requests</label>
                    <textarea class="form-control" name="solicitudes"></textarea>
                </div>
                <button type="submit" class="btn btn-gold">Confirm Reservation</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/reserve")
def process_reservation(
    room_id: int = Form(...),
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
    num_huespedes: int = Form(...),
    fecha_checkin: str = Form(...),
    fecha_checkout: str = Form(...),
    solicitudes: str = Form(None),
    db: SessionLocal = Depends(get_db),
):
    # Validate dates
    try:
        checkin = datetime.datetime.strptime(fecha_checkin, "%Y-%m-%d").date()
        checkout = datetime.datetime.strptime(fecha_checkout, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    if checkin >= checkout:
        raise HTTPException(status_code=400, detail="Check‑in must be before check‑out")
    # Verify room exists
    room = db.query(Habitacion).filter(Habitacion.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    # Availability check: no overlapping confirmed reservation
    overlapping = (
        db.query(Reserva)
        .filter(
            Reserva.habitacion_id == room_id,
            Reserva.estado == "confirmada",
            Reserva.fecha_checkin < checkout,
            Reserva.fecha_checkout > checkin,
        )
        .first()
    )
    if overlapping:
        raise HTTPException(status_code=409, detail="Room not available for selected dates")
    # Get or create client
    client = db.query(Cliente).filter(Cliente.email == email).first()
    if not client:
        client = Cliente(nombre=nombre, email=email, telefono=telefono)
        db.add(client)
        db.commit()
        db.refresh(client)
    # Create reservation
    referencia = generate_reference()
    reserva = Reserva(
        cliente_id=client.id,
        habitacion_id=room.id,
        fecha_checkin=checkin,
        fecha_checkout=checkout,
        num_huespedes=num_huespedes,
        solicitudes=solicitudes,
        estado="pendiente",
        referencia=referencia,
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    # Send confirmation email (optional)
    send_confirmation_email(email, nombre, referencia)
    # Redirect to confirmation page
    return RedirectResponse(url=f"/confirmation?ref={referencia}", status_code=303)


@app.get("/confirmation", response_class=HTMLResponse)
def confirmation_page(ref: str, db: SessionLocal = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.referencia == ref).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reservation not found")
    room = reserva.habitacion
    client = reserva.cliente
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <title>Confirmation</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .btn-gold {{background:#DAA520;color:#fff;}}
            .card-header {{background:#003366;color:#fff;}}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark" style="background:#003366;">
          <div class="container-fluid">
            <a class="navbar-brand" href="/">Hotel Paradise</a>
          </div>
        </nav>
        <div class="container py-4">
            <div class="card">
                <div class="card-header">
                    Reservation Reference: <strong>{reserva.referencia}</strong>
                </div>
                <div class="card-body">
                    <p><strong>Name:</strong> {client.nombre}</p>
                    <p><strong>Email:</strong> {client.email}</p>
                    <p><strong>Phone:</strong> {client.telefono}</p>
                    <p><strong>Room:</strong> {room.tipo}</p>
                    <p><strong>Check‑in:</strong> {reserva.fecha_checkin}</p>
                    <p><strong>Check‑out:</strong> {reserva.fecha_checkout}</p>
                    <p><strong>Guests:</strong> {reserva.num_huespedes}</p>
                    <p><strong>Special Requests:</strong> {reserva.solicitudes or ''}</p>
                    <p><strong>Status:</strong> {reserva.estado}</p>
                    <a href="/" class="btn btn-gold">Back to Home</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ----------------------------------------------------------------------
# Admin area (basic auth)
# ----------------------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(verify_admin)])
def admin_dashboard(db: SessionLocal = Depends(get_db)):
    reservas = db.query(Reserva).order_by(Reserva.fecha_creacion.desc()).all()
    rows = ""
    for r in reservas:
        rows += f"""
        <tr>
            <td>{r.referencia}</td>
            <td>{r.cliente.nombre}</td>
            <td>{r.habitacion.tipo}</td>
            <td>{r.fecha_checkin}</td>
            <td>{r.fecha_checkout}</td>
            <td>{r.estado}</td>
            <td>
                <form method="post" action="/admin/update_status" style="display:inline;">
                    <input type="hidden" name="reserva_id" value="{r.id}">
                    <select name="estado" class="form-select form-select-sm d-inline w-auto">
                        <option value="pendiente" {"selected" if r.estado=="pendiente" else ""}>pendiente</option>
                        <option value="confirmada" {"selected" if r.estado=="confirmada" else ""}>confirmada</option>
                        <option value="cancelada" {"selected" if r.estado=="cancelada" else ""}>cancelada</option>
                    </select>
                    <button type="submit" class="btn btn-sm btn-danger">Update</button>
                </form>
            </td>
        </tr>
        """
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <title>Admin Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .btn-gold {{background:#DAA520;color:#fff;}}
            .table-hover tbody tr:hover {{background:#f1f1f1;}}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark" style="background:#003366;">
          <div class="container-fluid">
            <a class="navbar-brand" href="/">Hotel Admin</a>
          </div>
        </nav>
        <div class="container py-4">
            <h2 class="mb-4">Reservations</h2>
            <a href="/admin/export" class="btn btn-gold mb-3">Export CSV</a>
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Reference</th>
                        <th>Name</th>
                        <th>Room</th>
                        <th>Check‑in</th>
                        <th>Check‑out</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/admin/update_status", dependencies=[Depends(verify_admin)])
def update_status(reserva_id: int = Form(...), estado: str = Form(...), db: SessionLocal = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if estado not in ("pendiente", "confirmada", "cancelada"):
        raise HTTPException(status_code=400, detail="Invalid status")
    reserva.estado = estado
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin/export")
def export_csv(db: SessionLocal = Depends(get_db), _: bool = Depends(verify_admin)):
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Reference",
            "Client Name",
            "Email",
            "Phone",
            "Room Type",
            "Check-in",
            "Check-out",
            "Guests",
            "Special Requests",
            "Status",
            "Created",
        ]
    )
    reservas = db.query(Reserva).all()
    for r in reservas:
        writer.writerow(
            [
                r.referencia,
                r.cliente.nombre,
                r.cliente.email,
                r.cliente.telefono,
                r.habitacion.tipo,
                r.fecha_checkin,
                r.fecha_checkout,
                r.num_huespedes,
                r.solicitudes or "",
                r.estado,
                r.fecha_creacion,
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reservas.csv"},
    )


# ----------------------------------------------------------------------
# API endpoints (admin protected)
# ----------------------------------------------------------------------
@app.get("/api/reservas")
def api_list_reservas(db: SessionLocal = Depends(get_db), _: bool = Depends(verify_admin)):
    reservas = db.query(Reserva).all()
    result = []
    for r in reservas:
        result.append(
            {
                "id": r.id,
                "reference": r.referencia,
                "client": {"name": r.cliente.nombre, "email": r.cliente.email},
                "room": r.habitacion.tipo,
                "checkin": str(r.fecha_checkin),
                "checkout": str(r.fecha_checkout),
                "guests": r.num_huespedes,
                "status": r.estado,
            }
        )
    return result


@app.post("/api/reservas")
def api_create_reserva(
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
    room_id: int = Form(...),
    num_huespedes: int = Form(...),
    fecha_checkin: str = Form(...),
    fecha_checkout: str = Form(...),
    solicitudes: str = Form(None),
    db: SessionLocal = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    checkin = datetime.datetime.strptime(fecha_checkin, "%Y-%m-%d").date()
    checkout = datetime.datetime.strptime(fecha_checkout, "%Y-%m-%d").date()
    if checkin >= checkout:
        raise HTTPException(status_code=400, detail="Invalid dates")
    room = db.query(Habitacion).filter(Habitacion.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    client = db.query(Cliente).filter(Cliente.email == email).first()
    if not client:
        client = Cliente(nombre=nombre, email=email, telefono=telefono)
        db.add(client)
        db.commit()
        db.refresh(client)
    referencia = generate_reference()
    reserva = Reserva(
        cliente_id=client.id,
        habitacion_id=room.id,
        fecha_checkin=checkin,
        fecha_checkout=checkout,
        num_huespedes=num_huespedes,
        solicitudes=solicitudes,
        estado="pendiente",
        referencia=referencia,
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return {"reference": referencia, "id": reserva.id}


@app.get("/api/reservas/{reserva_id}")
def api_get_reserva(reserva_id: int, db: SessionLocal = Depends(get_db), _: bool = Depends(verify_admin)):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return {
        "id": r.id,
        "reference": r.referencia,
        "client": {"name": r.cliente.nombre, "email": r.cliente.email},
        "room": r.habitacion.tipo,
        "checkin": str(r.fecha_checkin),
        "checkout": str(r.fecha_checkout),
        "guests": r.num_huespedes,
        "status": r.estado,
    }


@app.put("/api/reservas/{reserva_id}")
def api_update_reserva(
    reserva_id: int,
    estado: str = Form(...),
    db: SessionLocal = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if estado not in ("pendiente", "confirmada", "cancelada"):
        raise HTTPException(status_code=400, detail="Invalid status")
    r.estado = estado
    db.commit()
    return {"message": "Updated"}


@app.delete("/api/reservas/{reserva_id}")
def api_delete_reserva(reserva_id: int, db: SessionLocal = Depends(get_db), _: bool = Depends(verify_admin)):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    db.delete(r)
    db.commit()
    return {"message": "Deleted"}


# ----------------------------------------------------------------------
# Startup event: populate rooms if empty
# ----------------------------------------------------------------------
@app.on_event("startup")
def startup_populate():
    db = SessionLocal()
    if db.query(Habitacion).count() == 0:
        sample_rooms = [
            {
                "tipo": "Standard",
                "precio_noche": 100,
                "descripcion": "Cozy standard room",
                "capacidad": 2,
                "disponibilidad": True,
            },
            {
                "tipo": "Deluxe",
                "precio_noche": 180,
                "descripcion": "Spacious deluxe room with view",
                "capacidad": 3,
                "disponibilidad": True,
            },
            {
                "tipo": "Suite",
                "precio_noche": 250,
                "descripcion": "Luxury suite with living area",
                "capacidad": 4,
                "disponibilidad": True,
            },
        ]
        for r in sample_rooms:
            db.add(Habitacion(**r))
        db.commit()
    db.close()


# ----------------------------------------------------------------------
# Run with uvicorn
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))