from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='operator')  # admin, operator, viewer
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    capacity = db.Column(db.String(50))
    is_returnable = db.Column(db.Boolean, default=False)
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='unidad')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def stock_status(self):
        if self.stock <= 0:
            return 'danger'
        elif self.min_stock > 0 and self.stock <= self.min_stock:
            return 'warning'
        return 'success'

    @property
    def stock_badge(self):
        return {'danger': 'Sin Stock', 'warning': 'Stock Bajo', 'success': 'OK'}.get(self.stock_status, 'OK')

    def __repr__(self):
        return f'<Product {self.name}>'


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    distributions = db.relationship('Distribution', backref='vehicle', lazy=True)

    def __repr__(self):
        return f'<Vehicle {self.code}>'


class Driver(db.Model):
    __tablename__ = 'drivers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)

    vehicle = db.relationship('Vehicle', backref='drivers')
    distributions = db.relationship('Distribution', backref='driver', lazy=True)

    def __repr__(self):
        return f'<Driver {self.name}>'


class ProductionRecord(db.Model):
    __tablename__ = 'production_records'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='production_records')
    user = db.relationship('User', backref='production_records')

    def __repr__(self):
        return f'<ProductionRecord {self.date} {self.product.name} x{self.quantity}>'


class Distribution(db.Model):
    __tablename__ = 'distributions'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    status = db.Column(db.String(20), default='salida')  # salida, retornado
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    returned_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='distributions')
    items = db.relationship('DistributionItem', backref='distribution',
                            lazy=True, cascade='all, delete-orphan')

    @property
    def total_items_sent(self):
        return sum(item.qty_sent for item in self.items)

    @property
    def pending_returnables(self):
        total = 0
        for item in self.items:
            if item.product.is_returnable:
                pending = item.qty_sent - item.qty_returned_full - item.qty_returned_empty
                if pending > 0:
                    total += pending
        return total

    @property
    def status_badge(self):
        return {'salida': 'warning', 'retornado': 'success'}.get(self.status, 'secondary')

    @property
    def status_label(self):
        return {'salida': 'En Ruta', 'retornado': 'Retornado'}.get(self.status, self.status)

    def __repr__(self):
        return f'<Distribution {self.date} {self.vehicle.code}>'


class DistributionItem(db.Model):
    __tablename__ = 'distribution_items'

    id = db.Column(db.Integer, primary_key=True)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    qty_sent = db.Column(db.Integer, default=0)
    qty_returned_full = db.Column(db.Integer, default=0)
    qty_returned_empty = db.Column(db.Integer, default=0)

    product = db.relationship('Product', backref='distribution_items')

    @property
    def qty_sold(self):
        return self.qty_sent - self.qty_returned_full

    @property
    def qty_pending(self):
        if self.product.is_returnable:
            return max(0, self.qty_sent - self.qty_returned_full - self.qty_returned_empty)
        return 0

    def __repr__(self):
        return f'<DistributionItem {self.product.name} x{self.qty_sent}>'


class PlantSale(db.Model):
    __tablename__ = 'plant_sales'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    client_name = db.Column(db.String(100))
    sale_type = db.Column(db.String(20), default='contado')  # contado, credito
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='plant_sales')
    user = db.relationship('User', backref='plant_sales')

    def __repr__(self):
        return f'<PlantSale {self.date} {self.product.name} x{self.quantity}>'


class Breakage(db.Model):
    __tablename__ = 'breakages'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='breakages')
    user = db.relationship('User', backref='breakages')

    def __repr__(self):
        return f'<Breakage {self.date} {self.product.name} x{self.quantity}>'


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # entrada / salida
    balance_after = db.Column(db.Integer)
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(30))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='stock_movements')
    user = db.relationship('User', backref='stock_movements')

    MOVEMENT_LABELS = {
        'produccion': 'Producción',
        'distribucion_salida': 'Distribución (Salida)',
        'devolucion_lleno': 'Devolución (Producto Lleno)',
        'devolucion_vacio': 'Devolución (Envase Vacío)',
        'venta_planta': 'Venta en Planta',
        'rotura': 'Rotura / Baja',
        'ajuste_entrada': 'Ajuste (+)',
        'ajuste_salida': 'Ajuste (-)',
    }

    DIRECTION_COLORS = {
        'entrada': 'success',
        'salida': 'danger',
    }

    @property
    def type_label(self):
        return self.MOVEMENT_LABELS.get(self.movement_type, self.movement_type)

    @property
    def direction_color(self):
        return self.DIRECTION_COLORS.get(self.direction, 'secondary')

    def __repr__(self):
        return f'<StockMovement {self.date} {self.movement_type} x{self.quantity}>'


# ── Dispensers (tracking por código / número de serie) ────────────────────────

class Dispenser(db.Model):
    __tablename__ = 'dispensers'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # nro de serie
    model = db.Column(db.String(50), default='VIP')               # VIP, Antares 10, etc.
    status = db.Column(db.String(20), default='deposito')         # deposito, campo, taller
    current_client = db.Column(db.String(100))
    current_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    current_vehicle = db.relationship('Vehicle', backref='dispensers_assigned')
    movements = db.relationship('DispenserMovement', backref='dispenser',
                                lazy=True, order_by='DispenserMovement.date.desc()')

    STATUS_LABELS = {'deposito': 'En depósito', 'campo': 'En campo', 'taller': 'En taller'}
    STATUS_COLORS = {'deposito': 'success', 'campo': 'warning', 'taller': 'secondary'}

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')

    def __repr__(self):
        return f'<Dispenser {self.code}>'


class DispenserMovement(db.Model):
    __tablename__ = 'dispenser_movements'

    id = db.Column(db.Integer, primary_key=True)
    dispenser_id = db.Column(db.Integer, db.ForeignKey('dispensers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # salida, entrada, taller
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    client_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle = db.relationship('Vehicle', backref='dispenser_movements')
    user = db.relationship('User', backref='dispenser_movements')

    TYPE_LABELS = {'salida': 'Salida a cliente', 'entrada': 'Entrada / devuelto', 'taller': 'Enviado a taller'}
    TYPE_COLORS = {'salida': 'warning', 'entrada': 'success', 'taller': 'secondary'}

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.movement_type, self.movement_type)

    @property
    def type_color(self):
        return self.TYPE_COLORS.get(self.movement_type, 'secondary')

    def __repr__(self):
        return f'<DispenserMovement {self.dispenser.code} {self.movement_type} {self.date}>'


# ── Stock helpers ─────────────────────────────────────────────────────────────

def update_stock(product, quantity, direction, movement_type,
                 reference_id=None, reference_type=None,
                 notes=None, user_id=None, date=None):
    """Actualiza el stock del producto y registra el movimiento en el historial."""
    if date is None:
        date = datetime.utcnow().date()

    if direction == 'entrada':
        product.stock += quantity
    else:
        product.stock = max(0, product.stock - quantity)

    movement = StockMovement(
        date=date,
        product_id=product.id,
        movement_type=movement_type,
        quantity=quantity,
        direction=direction,
        balance_after=product.stock,
        reference_id=reference_id,
        reference_type=reference_type,
        notes=notes,
        user_id=user_id,
    )
    db.session.add(movement)
    return movement
