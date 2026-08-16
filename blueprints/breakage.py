from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Product, Breakage, update_stock

breakage_bp = Blueprint('breakage', __name__)

REASONS = [
    'Rotura accidental',
    'Vencimiento',
    'Contaminación',
    'Pérdida en tránsito',
    'Defecto de fabricación',
    'Otro',
]


@breakage_bp.route('/')
@login_required
def index():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    product_filter = request.args.get('product_id', '')

    query = Breakage.query.order_by(Breakage.date.desc(), Breakage.created_at.desc())

    if date_from:
        query = query.filter(Breakage.date >= date_from)
    if date_to:
        query = query.filter(Breakage.date <= date_to)
    if product_filter:
        query = query.filter(Breakage.product_id == int(product_filter))

    breakages = query.all()
    products = Product.query.filter_by(active=True).order_by(Product.name).all()
    total_lost = sum(b.quantity for b in breakages)

    return render_template('breakage/index.html',
                           breakages=breakages,
                           products=products,
                           total_lost=total_lost,
                           date_from=date_from,
                           date_to=date_to,
                           product_filter=product_filter)


@breakage_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def create():
    products = Product.query.filter_by(active=True).order_by(Product.name).all()

    if request.method == 'POST':
        date_str = request.form.get('date') or str(date.today())
        product_id = request.form.get('product_id', '')
        quantity_str = request.form.get('quantity', '')
        reason = request.form.get('reason', '').strip()
        notes = request.form.get('notes', '').strip()

        if not product_id or not quantity_str:
            flash('Producto y cantidad son obligatorios.', 'danger')
            return render_template('breakage/form.html', products=products,
                                   today=date.today(), reasons=REASONS)

        product = Product.query.get_or_404(int(product_id))
        qty = int(quantity_str)
        brk_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        breakage = Breakage(
            date=brk_date,
            product_id=product.id,
            quantity=qty,
            reason=reason,
            notes=notes,
            user_id=current_user.id,
        )
        db.session.add(breakage)
        db.session.flush()

        update_stock(
            product=product,
            quantity=qty,
            direction='salida',
            movement_type='rotura',
            reference_id=breakage.id,
            reference_type='breakage',
            notes=f'Rotura/Baja: {reason}',
            user_id=current_user.id,
            date=brk_date,
        )

        db.session.commit()
        flash(f'Rotura/Baja registrada: {qty} x {product.name}.', 'success')
        return redirect(url_for('breakage.index'))

    return render_template('breakage/form.html', products=products,
                           today=date.today(), reasons=REASONS)


@breakage_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('No tenés permisos para eliminar registros.', 'danger')
        return redirect(url_for('breakage.index'))

    breakage = Breakage.query.get_or_404(id)
    product = breakage.product

    update_stock(
        product=product,
        quantity=breakage.quantity,
        direction='entrada',
        movement_type='ajuste_entrada',
        reference_id=breakage.id,
        reference_type='breakage_delete',
        notes=f'Reversión de rotura del {breakage.date}',
        user_id=current_user.id,
        date=date.today(),
    )

    db.session.delete(breakage)
    db.session.commit()
    flash('Registro de rotura eliminado y stock revertido.', 'info')
    return redirect(url_for('breakage.index'))
