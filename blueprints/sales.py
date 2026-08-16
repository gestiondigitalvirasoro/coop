from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Product, PlantSale, update_stock

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/')
@login_required
def index():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    product_filter = request.args.get('product_id', '')

    query = PlantSale.query.order_by(PlantSale.date.desc(), PlantSale.created_at.desc())

    if date_from:
        query = query.filter(PlantSale.date >= date_from)
    if date_to:
        query = query.filter(PlantSale.date <= date_to)
    if product_filter:
        query = query.filter(PlantSale.product_id == int(product_filter))

    sales = query.all()
    products = Product.query.filter_by(active=True).order_by(Product.name).all()
    total_sold = sum(s.quantity for s in sales)

    return render_template('sales/index.html',
                           sales=sales,
                           products=products,
                           total_sold=total_sold,
                           date_from=date_from,
                           date_to=date_to,
                           product_filter=product_filter)


@sales_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def create():
    products = Product.query.filter_by(active=True).order_by(Product.name).all()

    if request.method == 'POST':
        date_str = request.form.get('date') or str(date.today())
        product_id = request.form.get('product_id', '')
        quantity_str = request.form.get('quantity', '')
        client_name = request.form.get('client_name', '').strip()
        sale_type = request.form.get('sale_type', 'contado')
        notes = request.form.get('notes', '').strip()

        if not product_id or not quantity_str:
            flash('Producto y cantidad son obligatorios.', 'danger')
            return render_template('sales/form.html', products=products, today=date.today())

        product = Product.query.get_or_404(int(product_id))
        qty = int(quantity_str)

        if product.stock < qty:
            flash(f'Stock insuficiente. Disponible: {product.stock} unidades.', 'danger')
            return render_template('sales/form.html', products=products, today=date.today())

        sale_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        sale = PlantSale(
            date=sale_date,
            product_id=product.id,
            quantity=qty,
            client_name=client_name,
            sale_type=sale_type,
            notes=notes,
            user_id=current_user.id,
        )
        db.session.add(sale)
        db.session.flush()

        update_stock(
            product=product,
            quantity=qty,
            direction='salida',
            movement_type='venta_planta',
            reference_id=sale.id,
            reference_type='sale',
            notes=f'Venta en planta{" - " + client_name if client_name else ""}',
            user_id=current_user.id,
            date=sale_date,
        )

        db.session.commit()
        flash(f'Venta registrada: {qty} x {product.name}.', 'success')
        return redirect(url_for('sales.index'))

    return render_template('sales/form.html', products=products, today=date.today())


@sales_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('No tenés permisos para eliminar ventas.', 'danger')
        return redirect(url_for('sales.index'))

    sale = PlantSale.query.get_or_404(id)
    product = sale.product

    update_stock(
        product=product,
        quantity=sale.quantity,
        direction='entrada',
        movement_type='ajuste_entrada',
        reference_id=sale.id,
        reference_type='sale_delete',
        notes=f'Reversión venta del {sale.date}',
        user_id=current_user.id,
        date=date.today(),
    )

    db.session.delete(sale)
    db.session.commit()
    flash('Venta eliminada y stock revertido.', 'info')
    return redirect(url_for('sales.index'))
