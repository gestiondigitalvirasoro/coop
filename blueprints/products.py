from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Product, Category, Vehicle, Driver

products_bp = Blueprint('products', __name__)


# ── Productos ──────────────────────────────────────────────────────────────────

@products_bp.route('/')
@login_required
def index():
    category_filter = request.args.get('category', '')
    status_filter = request.args.get('status', '')

    query = Product.query.filter_by(active=True)

    if category_filter:
        query = query.filter_by(category_id=int(category_filter))

    if status_filter == 'bajo':
        query = query.filter(Product.min_stock > 0, Product.stock <= Product.min_stock)
    elif status_filter == 'sin_stock':
        query = query.filter(Product.stock <= 0)

    products = query.order_by(Product.category_id, Product.name).all()
    categories = Category.query.order_by(Category.name).all()

    return render_template('products/index.html',
                           products=products,
                           categories=categories,
                           category_filter=category_filter,
                           status_filter=status_filter)


@products_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def create():
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', '')
        capacity = request.form.get('capacity', '').strip()
        is_returnable = bool(request.form.get('is_returnable'))
        min_stock = int(request.form.get('min_stock') or 0)
        initial_stock = int(request.form.get('initial_stock') or 0)
        unit = request.form.get('unit', 'unidad').strip()

        if not name or not category_id:
            flash('Nombre y categoría son obligatorios.', 'danger')
            return render_template('products/form.html', product=None, categories=categories)

        product = Product(
            name=name,
            category_id=int(category_id),
            capacity=capacity,
            is_returnable=is_returnable,
            min_stock=min_stock,
            stock=initial_stock,
            unit=unit,
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Producto "{name}" creado correctamente.', 'success')
        return redirect(url_for('products.index'))

    return render_template('products/form.html', product=None, categories=categories)


@products_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit(id):
    product = Product.query.get_or_404(id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', '')

        if not name or not category_id:
            flash('Nombre y categoría son obligatorios.', 'danger')
            return render_template('products/form.html', product=product, categories=categories)

        product.name = name
        product.category_id = int(category_id)
        product.capacity = request.form.get('capacity', '').strip()
        product.is_returnable = bool(request.form.get('is_returnable'))
        product.min_stock = int(request.form.get('min_stock') or 0)
        product.unit = request.form.get('unit', 'unidad').strip()

        db.session.commit()
        flash(f'Producto "{product.name}" actualizado.', 'success')
        return redirect(url_for('products.index'))

    return render_template('products/form.html', product=product, categories=categories)


@products_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    product = Product.query.get_or_404(id)
    product.active = False
    db.session.commit()
    flash(f'Producto "{product.name}" desactivado.', 'info')
    return redirect(url_for('products.index'))


@products_bp.route('/<int:id>/ajuste', methods=['POST'])
@login_required
def adjust_stock(id):
    from models import update_stock
    from datetime import date
    product = Product.query.get_or_404(id)
    qty = int(request.form.get('quantity', 0))
    direction = request.form.get('direction', 'entrada')
    notes = request.form.get('notes', '').strip()

    if qty <= 0:
        flash('La cantidad debe ser mayor a cero.', 'danger')
        return redirect(url_for('products.index'))

    movement_type = 'ajuste_entrada' if direction == 'entrada' else 'ajuste_salida'
    update_stock(product, qty, direction, movement_type,
                 notes=notes or f'Ajuste manual de stock',
                 user_id=current_user.id,
                 date=date.today())
    db.session.commit()
    flash(f'Stock de "{product.name}" ajustado: {direction} {qty} unidades.', 'success')
    return redirect(url_for('products.index'))


# ── Categorías ─────────────────────────────────────────────────────────────────

@products_bp.route('/categorias')
@login_required
def categories():
    cats = Category.query.order_by(Category.name).all()
    return render_template('products/categories.html', categories=cats)


@products_bp.route('/categorias/nueva', methods=['GET', 'POST'])
@login_required
def create_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('El nombre es obligatorio.', 'danger')
        elif Category.query.filter_by(name=name).first():
            flash('Ya existe una categoría con ese nombre.', 'danger')
        else:
            db.session.add(Category(name=name, description=description))
            db.session.commit()
            flash(f'Categoría "{name}" creada.', 'success')
            return redirect(url_for('products.categories'))

    return render_template('products/category_form.html', category=None)


@products_bp.route('/categorias/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    cat = Category.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('El nombre es obligatorio.', 'danger')
        else:
            cat.name = name
            cat.description = request.form.get('description', '').strip()
            db.session.commit()
            flash('Categoría actualizada.', 'success')
            return redirect(url_for('products.categories'))

    return render_template('products/category_form.html', category=cat)


# ── Vehículos y Choferes ───────────────────────────────────────────────────────

@products_bp.route('/vehiculos')
@login_required
def vehicles():
    vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()
    drivers = Driver.query.filter_by(active=True).order_by(Driver.name).all()
    return render_template('products/vehicles.html', vehicles=vehicles, drivers=drivers)


@products_bp.route('/vehiculos/nuevo', methods=['POST'])
@login_required
def create_vehicle():
    code = request.form.get('code', '').strip()
    description = request.form.get('description', '').strip()

    if not code:
        flash('El código del móvil es obligatorio.', 'danger')
    elif Vehicle.query.filter_by(code=code).first():
        flash('Ya existe un móvil con ese código.', 'danger')
    else:
        db.session.add(Vehicle(code=code, description=description))
        db.session.commit()
        flash(f'Móvil "{code}" creado.', 'success')

    return redirect(url_for('products.vehicles'))


@products_bp.route('/vehiculos/<int:id>/eliminar', methods=['POST'])
@login_required
def delete_vehicle(id):
    v = Vehicle.query.get_or_404(id)
    v.active = False
    db.session.commit()
    flash(f'Móvil "{v.code}" desactivado.', 'info')
    return redirect(url_for('products.vehicles'))


@products_bp.route('/choferes/nuevo', methods=['POST'])
@login_required
def create_driver():
    name = request.form.get('name', '').strip()
    vehicle_id = request.form.get('vehicle_id') or None

    if not name:
        flash('El nombre del chofer es obligatorio.', 'danger')
    else:
        db.session.add(Driver(name=name,
                               vehicle_id=int(vehicle_id) if vehicle_id else None))
        db.session.commit()
        flash(f'Chofer "{name}" creado.', 'success')

    return redirect(url_for('products.vehicles'))


@products_bp.route('/choferes/<int:id>/eliminar', methods=['POST'])
@login_required
def delete_driver(id):
    d = Driver.query.get_or_404(id)
    d.active = False
    db.session.commit()
    flash(f'Chofer "{d.name}" desactivado.', 'info')
    return redirect(url_for('products.vehicles'))
