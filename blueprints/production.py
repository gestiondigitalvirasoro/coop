from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Product, ProductionRecord, update_stock

production_bp = Blueprint('production', __name__)


@production_bp.route('/')
@login_required
def index():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    product_filter = request.args.get('product_id', '')

    query = ProductionRecord.query.order_by(
        ProductionRecord.date.desc(), ProductionRecord.created_at.desc()
    )

    if date_from:
        query = query.filter(ProductionRecord.date >= date_from)
    if date_to:
        query = query.filter(ProductionRecord.date <= date_to)
    if product_filter:
        query = query.filter(ProductionRecord.product_id == int(product_filter))

    records = query.all()
    products = Product.query.filter_by(active=True).order_by(Product.name).all()
    total_produced = sum(r.quantity for r in records)

    return render_template('production/index.html',
                           records=records,
                           products=products,
                           total_produced=total_produced,
                           date_from=date_from,
                           date_to=date_to,
                           product_filter=product_filter)


@production_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def create():
    products = Product.query.filter_by(active=True).order_by(Product.name).all()

    if request.method == 'POST':
        date_str = request.form.get('date') or str(date.today())
        product_id = request.form.get('product_id', '')
        quantity_str = request.form.get('quantity', '')
        notes = request.form.get('notes', '').strip()

        if not product_id or not quantity_str:
            flash('Producto y cantidad son obligatorios.', 'danger')
            return render_template('production/form.html', products=products, today=date.today())

        product = Product.query.get_or_404(int(product_id))
        qty = int(quantity_str)
        prod_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        record = ProductionRecord(
            date=prod_date,
            product_id=product.id,
            quantity=qty,
            notes=notes,
            user_id=current_user.id,
        )
        db.session.add(record)
        db.session.flush()

        update_stock(
            product=product,
            quantity=qty,
            direction='entrada',
            movement_type='produccion',
            reference_id=record.id,
            reference_type='production',
            notes=f'Producción registrada: {qty} x {product.name}',
            user_id=current_user.id,
            date=prod_date,
        )

        db.session.commit()
        flash(f'Producción registrada: {qty} x {product.name}.', 'success')
        return redirect(url_for('production.index'))

    return render_template('production/form.html', products=products, today=date.today())


@production_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('No tenés permisos para eliminar registros.', 'danger')
        return redirect(url_for('production.index'))

    record = ProductionRecord.query.get_or_404(id)
    product = record.product

    update_stock(
        product=product,
        quantity=record.quantity,
        direction='salida',
        movement_type='ajuste_salida',
        reference_id=record.id,
        reference_type='production_delete',
        notes=f'Reversión de producción del {record.date}',
        user_id=current_user.id,
        date=date.today(),
    )

    db.session.delete(record)
    db.session.commit()
    flash('Registro de producción eliminado y stock revertido.', 'info')
    return redirect(url_for('production.index'))
