from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Product, Vehicle, Driver, Distribution, DistributionItem, update_stock

distribution_bp = Blueprint('distribution', __name__)


@distribution_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    vehicle_filter = request.args.get('vehicle_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Distribution.query.order_by(Distribution.date.desc(), Distribution.created_at.desc())

    if status_filter:
        query = query.filter_by(status=status_filter)
    if vehicle_filter:
        query = query.filter_by(vehicle_id=int(vehicle_filter))
    if date_from:
        query = query.filter(Distribution.date >= date_from)
    if date_to:
        query = query.filter(Distribution.date <= date_to)

    distributions = query.all()
    vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()

    return render_template('distribution/index.html',
                           distributions=distributions,
                           vehicles=vehicles,
                           status_filter=status_filter,
                           vehicle_filter=vehicle_filter,
                           date_from=date_from,
                           date_to=date_to)


@distribution_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def create():
    vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()
    drivers = Driver.query.filter_by(active=True).order_by(Driver.name).all()
    products = Product.query.filter_by(active=True).order_by(Product.name).all()

    if request.method == 'POST':
        date_str = request.form.get('date') or str(date.today())
        vehicle_id = request.form.get('vehicle_id', '')
        driver_id = request.form.get('driver_id', '')
        notes = request.form.get('notes', '').strip()
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        if not vehicle_id or not driver_id:
            flash('Móvil y chofer son obligatorios.', 'danger')
            return render_template('distribution/form.html',
                                   vehicles=vehicles, drivers=drivers,
                                   products=products, today=date.today())

        valid_items = [(pid, qty) for pid, qty in zip(product_ids, quantities)
                       if pid and qty and int(qty) > 0]

        if not valid_items:
            flash('Agregá al menos un producto con cantidad mayor a cero.', 'danger')
            return render_template('distribution/form.html',
                                   vehicles=vehicles, drivers=drivers,
                                   products=products, today=date.today())

        dist_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        dist = Distribution(
            date=dist_date,
            vehicle_id=int(vehicle_id),
            driver_id=int(driver_id),
            notes=notes,
            user_id=current_user.id,
            status='salida',
        )
        db.session.add(dist)
        db.session.flush()

        vehicle = dist.vehicle

        for pid, qty_str in valid_items:
            product = Product.query.get(int(pid))
            qty = int(qty_str)

            item = DistributionItem(
                distribution_id=dist.id,
                product_id=product.id,
                qty_sent=qty,
            )
            db.session.add(item)

            update_stock(
                product=product,
                quantity=qty,
                direction='salida',
                movement_type='distribucion_salida',
                reference_id=dist.id,
                reference_type='distribution',
                notes=f'Carga {vehicle.code} - {dist.driver.name}',
                user_id=current_user.id,
                date=dist_date,
            )

        db.session.commit()
        flash(f'Distribución registrada para {vehicle.code}.', 'success')
        return redirect(url_for('distribution.index'))

    return render_template('distribution/form.html',
                           vehicles=vehicles, drivers=drivers,
                           products=products, today=date.today())


@distribution_bp.route('/<int:id>')
@login_required
def detail(id):
    dist = Distribution.query.get_or_404(id)
    return render_template('distribution/detail.html', dist=dist)


@distribution_bp.route('/<int:id>/devolucion', methods=['GET', 'POST'])
@login_required
def register_return(id):
    dist = Distribution.query.get_or_404(id)

    if dist.status == 'retornado':
        flash('Esta distribución ya fue retornada.', 'warning')
        return redirect(url_for('distribution.detail', id=id))

    if request.method == 'POST':
        error = False
        for item in dist.items:
            qty_full = int(request.form.get(f'returned_full_{item.id}', 0) or 0)
            qty_empty = int(request.form.get(f'returned_empty_{item.id}', 0) or 0)

            if qty_full + qty_empty > item.qty_sent:
                flash(f'Error en "{item.product.name}": la suma de devoluciones supera la cantidad enviada ({item.qty_sent}).', 'danger')
                error = True
                break

            item.qty_returned_full = qty_full
            item.qty_returned_empty = qty_empty

            if qty_full > 0:
                update_stock(
                    product=item.product,
                    quantity=qty_full,
                    direction='entrada',
                    movement_type='devolucion_lleno',
                    reference_id=dist.id,
                    reference_type='distribution',
                    notes=f'Devolución llena {dist.vehicle.code} del {dist.date}',
                    user_id=current_user.id,
                    date=date.today(),
                )

        if not error:
            dist.status = 'retornado'
            dist.returned_at = datetime.utcnow()
            db.session.commit()
            flash(f'Devolución registrada para {dist.vehicle.code}.', 'success')
            return redirect(url_for('distribution.detail', id=id))
        else:
            db.session.rollback()

    return render_template('distribution/return_form.html', dist=dist)


@distribution_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('No tenés permisos para eliminar distribuciones.', 'danger')
        return redirect(url_for('distribution.index'))

    dist = Distribution.query.get_or_404(id)

    if dist.status == 'salida':
        for item in dist.items:
            update_stock(
                product=item.product,
                quantity=item.qty_sent,
                direction='entrada',
                movement_type='ajuste_entrada',
                reference_id=dist.id,
                reference_type='distribution_delete',
                notes=f'Reversión distribución {dist.vehicle.code}',
                user_id=current_user.id,
                date=date.today(),
            )

    db.session.delete(dist)
    db.session.commit()
    flash('Distribución eliminada.', 'info')
    return redirect(url_for('distribution.index'))
