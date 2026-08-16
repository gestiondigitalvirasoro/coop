"""
Carga datos de simulación realistas basados en la planilla de Moncho.
Ejecutar DESPUÉS de init_db.py: python simulate.py
"""
from datetime import date, timedelta
from app import create_app
from models import db, Product, Vehicle, Driver, Distribution, DistributionItem
from models import ProductionRecord, PlantSale, Breakage, Dispenser, DispenserMovement
from models import User, update_stock

app = create_app()

def get(model, **kwargs):
    return model.query.filter_by(**kwargs).first()

def simulate():
    with app.app_context():

        admin = get(User, username='admin')

        # Productos
        p20m  = get(Product, name='20 Lts Mesa')
        p12m  = get(Product, name='12 Lts Mesa')
        pmin  = get(Product, name='20 L Mineral')
        p600t = get(Product, name='600 cc Tapa')
        p600p = get(Product, name='600 cc Pico')
        p15   = get(Product, name='1,5 Lts')
        pvip  = get(Product, name='Dispenser VIP')

        # Móviles
        v8  = get(Vehicle, code='Móvil 8')
        v20 = get(Vehicle, code='Móvil 20')
        v22 = get(Vehicle, code='Móvil 22')
        v25 = get(Vehicle, code='Móvil 25')

        # Choferes (uno por móvil)
        d8  = Driver.query.filter_by(vehicle_id=v8.id).first()
        d20 = Driver.query.filter_by(vehicle_id=v20.id).first()
        d22 = Driver.query.filter_by(vehicle_id=v22.id).first()
        d25 = Driver.query.filter_by(vehicle_id=v25.id).first()

        # ── PRODUCCIÓN (últimos 20 días) ───────────────────────────────────────
        prod_data = [
            # (días atrás, producto, cantidad)
            (20, p20m,  287), (20, p12m,   1), (20, p600t,  0), (20, p15,    0),
            (19, p20m,  140), (19, p600t, 48), (19, p600p, 12), (19, p15,   24),
            (18, p20m,  197), (18, p12m,   8), (18, pmin,  21),
            (17, p20m,  100), (17, p600t, 60), (17, p15,   30),
            (16, p20m,  174), (16, p600p, 24),
            (15, p20m,   95), (15, p12m,   5), (15, p600t, 72), (15, p15,   48),
            (14, p20m,  210), (14, pmin,  15),
            (13, p20m,  165), (13, p600t, 90), (13, p600p, 18), (13, p15,   36),
            (12, p20m,  140), (12, p12m,  10),
            (11, p20m,  220), (11, p600t, 60), (11, p15,   24),
            (10, p20m,  185), (10, pmin,  20), (10, p600p, 30),
            ( 9, p20m,  160), ( 9, p12m,   8), ( 9, p600t, 48),
            ( 8, p20m,  200), ( 8, p600t, 84), ( 8, p600p, 12), ( 8, p15,   48),
            ( 7, p20m,  175), ( 7, p12m,   4),
            ( 6, p20m,  190), ( 6, p600t, 60), ( 6, pmin,  18),
            ( 5, p20m,  210), ( 5, p600p, 24), ( 5, p15,   60),
            ( 4, p20m,  168), ( 4, p12m,   6), ( 4, p600t, 72),
            ( 3, p20m,  195), ( 3, p600t, 48), ( 3, p600p, 18), ( 3, p15,   36),
            ( 2, p20m,  220), ( 2, p12m,   5), ( 2, pmin,  12),
            ( 1, p20m,  180), ( 1, p600t, 66), ( 1, p15,   42),
        ]

        today = date.today()
        print('Cargando produccion...')
        for dias, prod, qty in prod_data:
            if qty == 0:
                continue
            d = today - timedelta(days=dias)
            rec = ProductionRecord(date=d, product_id=prod.id, quantity=qty,
                                   notes='Producción diaria', user_id=admin.id)
            db.session.add(rec)
            db.session.flush()
            update_stock(prod, qty, 'entrada', 'produccion',
                         reference_id=rec.id, reference_type='production',
                         user_id=admin.id, date=d)

        db.session.commit()
        print('  OK - produccion cargada')

        # ── DISTRIBUCIONES (últimos 15 días, retornadas) ───────────────────────
        dist_data = [
            # (dias_atras, vehiculo, chofer, [items: (prod, enviado, dev_lleno, dev_vacio)])
            (15, v20, d20, [(p20m, 84, 10, 52), (p12m, 2, 0, 2),  (p600t, 4, 0, 0)]),
            (15, v22, v22, [(p20m, 47, 6, 30),  (p12m, 0, 0, 0),  (p600t, 3, 1, 0)]),
            (15, v25, d25, [(p20m, 46, 5, 28),  (p15,  1, 0, 0)]),

            (14, v20, d20, [(p20m, 100, 8, 68), (p12m, 2, 0, 2),  (p600t, 4, 0, 0)]),
            (14, v22, d22, [(p20m, 46,  4, 31), (p600t, 3, 0, 0)]),
            (14, v25, d25, [(p20m, 45,  5, 27), (p12m, 2, 0, 2)]),

            (13, v20, d20, [(p20m, 71,  6, 40), (p600t, 2, 0, 0), (p15, 2, 0, 0)]),
            (13, v22, d22, [(p20m, 40,  3, 28), (p12m, 1, 0, 1)]),
            (13, v25, d25, [(p20m, 55,  4, 35), (p600p, 1, 0, 0)]),

            (12, v20, d20, [(p20m, 92,  7, 58), (p12m, 3, 0, 3)]),
            (12, v22, d22, [(p20m, 50,  5, 33), (p600t, 5, 1, 0)]),
            (12, v8,  d8,  [(p20m, 27,  2, 18), (p600t, 3, 0, 0)]),

            (11, v20, d20, [(p20m, 84,  6, 55), (p12m, 2, 0, 2), (p600p, 2, 0, 0)]),
            (11, v22, d22, [(p20m, 40,  4, 27)]),
            (11, v25, d25, [(p20m, 48,  5, 29), (p15, 3, 0, 0)]),

            (10, v20, d20, [(p20m, 98,  8, 62), (p12m, 1, 0, 1)]),
            (10, v22, d22, [(p20m, 56,  5, 38), (p600t, 3, 0, 0)]),
            (10, v25, d25, [(p20m, 40,  3, 25), (p600p, 2, 0, 0)]),

            ( 9, v20, d20, [(p20m, 80,  7, 52), (p12m, 2, 0, 2), (p600t, 4, 0, 0)]),
            ( 9, v22, d22, [(p20m, 46,  4, 30)]),
            ( 9, v8,  d8,  [(p20m, 23,  2, 15), (p600t, 2, 0, 0)]),

            ( 8, v20, d20, [(p20m, 96,  8, 62), (p12m, 3, 0, 3)]),
            ( 8, v22, d22, [(p20m, 50,  5, 33), (p600t, 4, 0, 0)]),
            ( 8, v25, d25, [(p20m, 48,  4, 30), (p15, 2, 0, 0)]),

            ( 7, v20, d20, [(p20m, 84,  6, 54), (p12m, 2, 0, 2)]),
            ( 7, v22, d22, [(p20m, 44,  4, 28)]),
            ( 7, v25, d25, [(p20m, 46,  4, 28), (p600p, 2, 0, 0)]),

            ( 6, v20, d20, [(p20m, 100, 8, 64), (p12m, 2, 0, 2), (p600t, 5, 0, 0)]),
            ( 6, v22, d22, [(p20m, 50,  4, 33)]),
            ( 6, v8,  d8,  [(p20m, 28,  2, 18)]),

            ( 5, v20, d20, [(p20m, 90,  8, 58), (p12m, 1, 0, 1)]),
            ( 5, v22, d22, [(p20m, 52,  5, 34), (p600t, 3, 0, 0)]),
            ( 5, v25, d25, [(p20m, 44,  4, 26), (p15, 2, 0, 0)]),

            ( 4, v20, d20, [(p20m, 88,  7, 56), (p12m, 2, 0, 2)]),
            ( 4, v22, d22, [(p20m, 48,  4, 31), (p600t, 4, 1, 0)]),
            ( 4, v25, d25, [(p20m, 42,  4, 24)]),

            ( 3, v20, d20, [(p20m, 92,  8, 60), (p12m, 2, 0, 2), (p600t, 3, 0, 0)]),
            ( 3, v22, d22, [(p20m, 50,  5, 33)]),
            ( 3, v8,  d8,  [(p20m, 24,  2, 15)]),
        ]

        print('Cargando distribuciones retornadas...')
        for dias, veh, chof, items in dist_data:
            # Si el chofer es en realidad el vehículo (error), buscar el chofer correcto
            if isinstance(chof, Vehicle):
                chof = Driver.query.filter_by(vehicle_id=chof.id).first()

            d_date = today - timedelta(days=dias)
            dist = Distribution(date=d_date, vehicle_id=veh.id, driver_id=chof.id,
                                status='retornado', user_id=admin.id)
            dist.returned_at = db.func.now()
            db.session.add(dist)
            db.session.flush()

            for prod, sent, ret_full, ret_empty in items:
                item = DistributionItem(
                    distribution_id=dist.id, product_id=prod.id,
                    qty_sent=sent, qty_returned_full=ret_full,
                    qty_returned_empty=ret_empty
                )
                db.session.add(item)
                # Stock: descontar enviado
                update_stock(prod, sent, 'salida', 'distribucion_salida',
                             reference_id=dist.id, reference_type='distribution',
                             user_id=admin.id, date=d_date)
                # Stock: sumar devueltos llenos
                if ret_full > 0:
                    update_stock(prod, ret_full, 'entrada', 'devolucion_lleno',
                                 reference_id=dist.id, reference_type='distribution',
                                 user_id=admin.id, date=d_date)

        db.session.commit()
        print('  OK - distribuciones retornadas')

        # ── DISTRIBUCIONES ACTIVAS (en ruta HOY) ──────────────────────────────
        print('Cargando distribuciones activas (hoy)...')
        active_dist_data = [
            (v20, d20, [(p20m, 64), (p12m, 2), (p600t, 4)]),
            (v22, d22, [(p20m, 40), (p600t, 3)]),
            (v25, d25, [(p20m, 28), (p15, 2)]),
        ]
        for veh, chof, items in active_dist_data:
            dist = Distribution(date=today, vehicle_id=veh.id, driver_id=chof.id,
                                status='salida', user_id=admin.id)
            db.session.add(dist)
            db.session.flush()
            for prod, sent in items:
                item = DistributionItem(
                    distribution_id=dist.id, product_id=prod.id, qty_sent=sent)
                db.session.add(item)
                update_stock(prod, sent, 'salida', 'distribucion_salida',
                             reference_id=dist.id, reference_type='distribution',
                             user_id=admin.id, date=today)

        db.session.commit()
        print('  OK - distribuciones activas')

        # ── VENTAS EN PLANTA ──────────────────────────────────────────────────
        print('Cargando ventas en planta...')
        venta_data = [
            ( 8, p20m,  2, 'García Juan'),
            ( 7, p600t, 6, ''),
            ( 6, p20m,  1, 'Rodríguez M.'),
            ( 5, p12m,  1, 'López Ana'),
            ( 4, p20m,  2, ''),
            ( 3, p600t, 12, 'Almacén Pepe'),
            ( 2, p20m,  1, 'Martínez'),
            ( 1, p20m,  3, 'Cooperativa interna'),
            ( 1, p600p, 6, ''),
            ( 0, p20m,  2, 'Ramírez C.'),
            ( 0, p600t, 24, 'Kiosco Don Jorge'),
        ]
        for dias, prod, qty, cliente in venta_data:
            s_date = today - timedelta(days=dias)
            sale = PlantSale(date=s_date, product_id=prod.id, quantity=qty,
                             client_name=cliente or None,
                             sale_type='contado', user_id=admin.id)
            db.session.add(sale)
            db.session.flush()
            update_stock(prod, qty, 'salida', 'venta_planta',
                         reference_id=sale.id, reference_type='sale',
                         user_id=admin.id, date=s_date)

        db.session.commit()
        print('  OK - ventas en planta')

        # ── ROTURAS ───────────────────────────────────────────────────────────
        print('Cargando roturas...')
        rotura_data = [
            (12, p600t, 6,  'Rotura accidental', 'Caída en línea de producción'),
            ( 9, p20m,  1,  'Rotura accidental', 'Bidón rajado'),
            ( 5, p600p, 3,  'Defecto de fabricación', ''),
            ( 2, p600t, 12, 'Vencimiento', 'Lote vencido stock planta'),
        ]
        for dias, prod, qty, reason, notes in rotura_data:
            b_date = today - timedelta(days=dias)
            brk = Breakage(date=b_date, product_id=prod.id, quantity=qty,
                           reason=reason, notes=notes or None, user_id=admin.id)
            db.session.add(brk)
            db.session.flush()
            update_stock(prod, qty, 'salida', 'rotura',
                         reference_id=brk.id, reference_type='breakage',
                         user_id=admin.id, date=b_date)

        db.session.commit()
        print('  OK - roturas')

        # ── DISPENSERS POR CÓDIGO ─────────────────────────────────────────────
        print('Cargando dispensers...')
        disp_codes = [
            ('457626', 'VIP',        'campo',    'Virvet',         v22),
            ('483467', 'VIP',        'campo',    'Municipal',      v22),
            ('349559', 'VIP',        'deposito', None,             None),
            ('345269', 'VIP',        'campo',    'Gural',          v22),
            ('276915', 'Antares 10', 'campo',    'Gural',          v22),
            ('276023', 'VIP',        'deposito', None,             None),
            ('325120', 'VIP',        'campo',    '',               v20),
            ('270635', 'VIP',        'campo',    'Aguirre',        v20),
            ('325134', 'Antares 10', 'campo',    'Navar',          v25),
            ('272274', 'VIP',        'deposito', None,             None),
            ('297034', 'VIP',        'taller',   'Taller Romero',  None),
            ('350380', 'VIP',        'campo',    '',               v20),
            ('287119', 'VIP',        'campo',    'Norford',        v20),
            ('350355', 'VIP',        'deposito', None,             None),
            ('421742', 'Antares 10', 'taller',   'Taller Romero',  None),
            ('349557', 'VIP',        'deposito', None,             None),
            ('ejecutivo', 'VIP',     'campo',    'Casa Virvet',    v20),
        ]

        for code, model, status, client, veh in disp_codes:
            d = Dispenser(code=code, model=model, status=status,
                          current_client=client or None,
                          current_vehicle_id=veh.id if veh else None)
            db.session.add(d)
            db.session.flush()

            # Movimiento de salida si está en campo
            if status in ('campo', 'taller'):
                mov_date = today - timedelta(days=7)
                m = DispenserMovement(
                    dispenser_id=d.id, date=mov_date,
                    movement_type='salida' if status == 'campo' else 'taller',
                    vehicle_id=veh.id if veh else None,
                    client_name=client or None,
                    user_id=admin.id
                )
                db.session.add(m)

        db.session.commit()
        print('  OK - dispensers cargados')

        # ── RESUMEN FINAL ─────────────────────────────────────────────────────
        from models import StockMovement
        print()
        print('='*55)
        print('SIMULACION COMPLETADA')
        print('='*55)
        print()
        print('STOCK ACTUAL:')
        for p in Product.query.filter_by(active=True).order_by(Product.category_id, Product.name).all():
            bar = '#' * min(p.stock // 10, 20)
            alert = ' << BAJO' if p.stock_status in ('danger','warning') else ''
            print(f'  {p.name:<28} {p.stock:>5} u.  {bar}{alert}')

        print()
        print('DISTRIBUCIONES HOY (en ruta):')
        for dist in Distribution.query.filter_by(date=today, status='salida').all():
            print(f'  {dist.vehicle.code} - {dist.driver.name}  ({dist.total_items_sent} items)')

        print()
        print('DISPENSERS:')
        print(f'  En deposito: {Dispenser.query.filter_by(status="deposito", active=True).count()}')
        print(f'  En campo:    {Dispenser.query.filter_by(status="campo",    active=True).count()}')
        print(f'  En taller:   {Dispenser.query.filter_by(status="taller",   active=True).count()}')
        print()
        print('  Inicia el servidor con: python app.py')
        print('  Abre el navegador en:   http://localhost:5000')


if __name__ == '__main__':
    simulate()
