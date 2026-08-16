"""
Inicializa la base de datos con datos de ejemplo.
Ejecutar: python init_db.py
"""
from datetime import date, timedelta
from app import create_app
from models import db, User, Category, Product, Vehicle, Driver, update_stock

app = create_app()


def init_database():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── Usuarios ──────────────────────────────────────────────────────────
        admin = User(username='admin', email='admin@cooperativa.com', role='admin')
        admin.set_password('admin123')

        operador = User(username='operador', email='operador@cooperativa.com', role='operator')
        operador.set_password('oper123')

        db.session.add_all([admin, operador])
        db.session.flush()

        # ── Categorías ────────────────────────────────────────────────────────
        cat_mesa    = Category(name='Agua de Mesa',    description='Bidones de agua purificada retornables')
        cat_mineral = Category(name='Agua Mineralizada', description='Bidones de agua mineralizada retornables')
        cat_bots    = Category(name='Botellas',        description='Botellas descartables 600cc y 1.5L')
        cat_disp    = Category(name='Dispenser',       description='Equipos dispensadores VIP')
        cat_ret     = Category(name='Retornables vacíos', description='Envases vacíos recuperados para rellenar')

        db.session.add_all([cat_mesa, cat_mineral, cat_bots, cat_disp, cat_ret])
        db.session.flush()

        # ── Productos (según planilla real de Moncho) ─────────────────────────
        products_data = [
            # Agua de mesa (bidones retornables)
            dict(name='20 Lts Mesa',    category_id=cat_mesa.id, capacity='20L',
                 is_returnable=True,  min_stock=30, stock=0),
            dict(name='12 Lts Mesa',    category_id=cat_mesa.id, capacity='12L',
                 is_returnable=True,  min_stock=15, stock=0),
            # Agua mineralizada
            dict(name='20 L Mineral',   category_id=cat_mineral.id, capacity='20L',
                 is_returnable=True,  min_stock=10, stock=0),
            # Botellas descartables
            dict(name='600 cc Tapa',    category_id=cat_bots.id, capacity='600cc',
                 is_returnable=False, min_stock=50, stock=0),
            dict(name='600 cc Pico',    category_id=cat_bots.id, capacity='600cc',
                 is_returnable=False, min_stock=30, stock=0),
            dict(name='1,5 Lts',        category_id=cat_bots.id, capacity='1.5L',
                 is_returnable=False, min_stock=30, stock=0),
            # Dispenser
            dict(name='Dispenser VIP',  category_id=cat_disp.id, capacity=None,
                 is_returnable=False, min_stock=2,  stock=0, unit='equipo'),
            # Retornables vacíos (envases que vuelven)
            dict(name='Retornable vacío 20L Mesa',    category_id=cat_ret.id, capacity='20L',
                 is_returnable=False, min_stock=0, stock=0),
            dict(name='Retornable vacío 12L Mesa',    category_id=cat_ret.id, capacity='12L',
                 is_returnable=False, min_stock=0, stock=0),
            dict(name='Retornable vacío 20L Mineral', category_id=cat_ret.id, capacity='20L',
                 is_returnable=False, min_stock=0, stock=0),
        ]

        product_objects = []
        for pd in products_data:
            p = Product(**pd)
            db.session.add(p)
            product_objects.append(p)

        db.session.flush()

        # Registrar stock inicial como movimientos
        for p in product_objects:
            if p.stock > 0:
                from models import StockMovement
                m = StockMovement(
                    date=date.today(),
                    product_id=p.id,
                    movement_type='ajuste_entrada',
                    quantity=p.stock,
                    direction='entrada',
                    balance_after=p.stock,
                    notes='Stock inicial del sistema',
                    user_id=admin.id,
                )
                db.session.add(m)

        # ── Vehículos (según planilla real de Moncho) ─────────────────────────
        v8  = Vehicle(code='Móvil 8',  description='')
        v20 = Vehicle(code='Móvil 20', description='')
        v22 = Vehicle(code='Móvil 22', description='')
        v25 = Vehicle(code='Móvil 25', description='')
        v28 = Vehicle(code='Móvil 28', description='')
        v3  = Vehicle(code='Móvil 3',  description='')

        db.session.add_all([v8, v20, v22, v25, v28, v3])
        db.session.flush()

        # ── Choferes ──────────────────────────────────────────────────────────
        db.session.add_all([
            Driver(name='Chofer Móvil 8',  vehicle_id=v8.id),
            Driver(name='Chofer Móvil 20', vehicle_id=v20.id),
            Driver(name='Chofer Móvil 22', vehicle_id=v22.id),
            Driver(name='Chofer Móvil 25', vehicle_id=v25.id),
            Driver(name='Chofer Móvil 28', vehicle_id=v28.id),
            Driver(name='Chofer Móvil 3',  vehicle_id=v3.id),
        ])

        db.session.commit()
        print('OK - Base de datos inicializada correctamente.')
        print()
        print('  Usuarios creados:')
        print('    admin     / admin123  (administrador)')
        print('    operador  / oper123   (operador)')
        print()
        print('  Productos: 10 cargados (segun planilla Moncho)')
        print('  Vehiculos: Movil 3, 8, 20, 22, 25, 28')
        print('  Choferes:  1 por movil (renombrar desde el sistema)')
        print()
        print('  Inicia el servidor con: python app.py')
        print('  Abre el navegador en:   http://localhost:5000')


if __name__ == '__main__':
    init_database()
