"""
Simula un día completo de trabajo para HOY:
  1. Cierra los retornos vencidos del 26/05
  2. Registra producción de hoy
  3. Despacha móviles hoy
  4. Ventas en planta hoy
"""
from datetime import date, timedelta
from app import create_app
from models import (db, Product, Vehicle, Driver, Distribution, DistributionItem,
                    ProductionRecord, PlantSale, User, update_stock)

app = create_app()

def get(model, **kwargs):
    return model.query.filter_by(**kwargs).first()

def cargar_dia():
    with app.app_context():
        today = date.today()
        admin = get(User, username='admin')

        p20m  = get(Product, name='20 Lts Mesa')
        p12m  = get(Product, name='12 Lts Mesa')
        pmin  = get(Product, name='20 L Mineral')
        p600t = get(Product, name='600 cc Tapa')
        p600p = get(Product, name='600 cc Pico')
        p15   = get(Product, name='1,5 Lts')

        v8  = get(Vehicle, code='Móvil 8')
        v20 = get(Vehicle, code='Móvil 20')
        v22 = get(Vehicle, code='Móvil 22')
        v25 = get(Vehicle, code='Móvil 25')

        d8  = Driver.query.filter_by(vehicle_id=v8.id).first()
        d20 = Driver.query.filter_by(vehicle_id=v20.id).first()
        d22 = Driver.query.filter_by(vehicle_id=v22.id).first()
        d25 = Driver.query.filter_by(vehicle_id=v25.id).first()

        # ── 1. CERRAR RETORNOS VENCIDOS (26/05) ───────────────────────────────
        print('Cerrando retornos pendientes del 26/05...')
        pending = Distribution.query.filter_by(status='salida').all()
        retorno_data = {
            # vehicle_id -> [(prod, ret_full, ret_empty)]
            v20.id: [(p20m, 8, 54), (p12m, 0, 2), (p600t, 0, 0)],
            v22.id: [(p20m, 4, 34), (p600t, 0, 0)],
            v25.id: [(p20m, 3, 23), (p15, 0, 0)],
        }
        for dist in pending:
            items_retorno = retorno_data.get(dist.vehicle_id, [])
            for item in dist.items:
                # buscar si hay datos de retorno para este producto
                datos = next((r for r in items_retorno if r[0].id == item.product_id), None)
                if datos:
                    _, ret_full, ret_empty = datos
                    item.qty_returned_full  = ret_full
                    item.qty_returned_empty = ret_empty
                    if ret_full > 0:
                        update_stock(item.product, ret_full, 'entrada', 'devolucion_lleno',
                                     reference_id=dist.id, reference_type='distribution',
                                     user_id=admin.id, date=today)
            dist.status = 'retornado'
        db.session.commit()
        print('  OK - retornos cerrados')

        # ── 2. PRODUCCIÓN DE HOY ───────────────────────────────────────────────
        print('Cargando produccion de hoy...')
        prod_hoy = [
            (p20m,  195),
            (p600t,  72),
            (p15,    36),
        ]
        for prod, qty in prod_hoy:
            rec = ProductionRecord(date=today, product_id=prod.id, quantity=qty,
                                   notes='Producción diaria', user_id=admin.id)
            db.session.add(rec)
            db.session.flush()
            update_stock(prod, qty, 'entrada', 'produccion',
                         reference_id=rec.id, reference_type='production',
                         user_id=admin.id, date=today)
        db.session.commit()
        print('  OK - produccion cargada (195 bidones 20L, 72 bot 600cc, 36 bot 1.5L)')

        # ── 3. DESPACHO DE MÓVILES HOY ────────────────────────────────────────
        print('Despachando moviles...')
        despacho = [
            (v20, d20, [(p20m, 70), (p12m, 2),  (p600t, 6)]),
            (v22, d22, [(p20m, 45), (p600t, 4)]),
            (v25, d25, [(p20m, 32), (p15,   3)]),
            (v8,  d8,  [(p20m, 22), (p600t, 2)]),
        ]
        for veh, chof, items in despacho:
            dist = Distribution(date=today, vehicle_id=veh.id, driver_id=chof.id,
                                status='salida', user_id=admin.id)
            db.session.add(dist)
            db.session.flush()
            for prod, sent in items:
                item = DistributionItem(distribution_id=dist.id,
                                        product_id=prod.id, qty_sent=sent)
                db.session.add(item)
                update_stock(prod, sent, 'salida', 'distribucion_salida',
                             reference_id=dist.id, reference_type='distribution',
                             user_id=admin.id, date=today)
        db.session.commit()
        print('  OK - Movil 20 (70+2+6), Movil 22 (45+4), Movil 25 (32+3), Movil 8 (22+2)')

        # ── 4. VENTAS EN PLANTA HOY ───────────────────────────────────────────
        print('Cargando ventas en planta...')
        ventas_hoy = [
            (p20m,  2, 'López María'),
            (p600t, 6, 'Almacén Ruiz'),
            (p15,   4, ''),
        ]
        for prod, qty, cliente in ventas_hoy:
            sale = PlantSale(date=today, product_id=prod.id, quantity=qty,
                             client_name=cliente or None,
                             sale_type='contado', user_id=admin.id)
            db.session.add(sale)
            db.session.flush()
            update_stock(prod, qty, 'salida', 'venta_planta',
                         reference_id=sale.id, reference_type='sale',
                         user_id=admin.id, date=today)
        db.session.commit()
        print('  OK - 2 bidones (Lopez Maria), 6 bot 600cc (Almacen Ruiz), 4 bot 1.5L')

        # ── RESUMEN ───────────────────────────────────────────────────────────
        print()
        print('='*55)
        print('DIA CARGADO:', today.strftime('%d/%m/%Y'))
        print('='*55)
        print()
        print('STOCK ACTUAL:')
        for p in Product.query.filter_by(active=True).order_by(Product.name).all():
            alert = ' << BAJO' if p.stock_status in ('danger', 'warning') else ''
            print(f'  {p.name:<30} {p.stock:>5} u.{alert}')
        print()
        print('MOVILES EN RUTA HOY:')
        for d in Distribution.query.filter_by(date=today, status='salida').all():
            print(f'  {d.vehicle.code} - {d.total_items_sent} items enviados')


if __name__ == '__main__':
    cargar_dia()
