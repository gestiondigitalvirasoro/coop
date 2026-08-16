from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Dispenser, DispenserMovement, Vehicle, Product, update_stock

dispensers_bp = Blueprint('dispensers', __name__)

MODELS = ['VIP', 'Antares 10', 'Estándar', 'Otro']


# ── Vista principal ────────────────────────────────────────────────────────────

@dispensers_bp.route('/')
@login_required
def index():
    mode = request.args.get('mode', 'codigo')   # 'codigo' o 'volumen'
    status_filter = request.args.get('status', '')

    # ── Modo por código ────────────────────────────────────────────────────────
    query = Dispenser.query.filter_by(active=True)
    if status_filter:
        query = query.filter_by(status=status_filter)
    dispensers = query.order_by(Dispenser.status, Dispenser.code).all()

    total_deposito = Dispenser.query.filter_by(active=True, status='deposito').count()
    total_campo    = Dispenser.query.filter_by(active=True, status='campo').count()
    total_taller   = Dispenser.query.filter_by(active=True, status='taller').count()

    # ── Modo por volumen ───────────────────────────────────────────────────────
    from models import Category
    cat_disp = Category.query.filter_by(name='Dispenser').first()
    vol_products = []
    if cat_disp:
        vol_products = Product.query.filter_by(category_id=cat_disp.id, active=True).all()

    vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()

    known_clients = db.session.query(DispenserMovement.client_name)\
        .filter(DispenserMovement.client_name.isnot(None),
                DispenserMovement.client_name != '')\
        .distinct().order_by(DispenserMovement.client_name).all()
    known_clients = [r[0] for r in known_clients]

    return render_template('dispensers/index.html',
                           mode=mode,
                           dispensers=dispensers,
                           total_deposito=total_deposito,
                           total_campo=total_campo,
                           total_taller=total_taller,
                           vol_products=vol_products,
                           vehicles=vehicles,
                           status_filter=status_filter,
                           known_clients=known_clients)


# ── Alta de dispenser (por código) ────────────────────────────────────────────

@dispensers_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        model = request.form.get('model', 'VIP').strip()
        notes = request.form.get('notes', '').strip()

        if not code:
            flash('El código / número de serie es obligatorio.', 'danger')
            return render_template('dispensers/form.html', dispenser=None, models=MODELS)

        if Dispenser.query.filter_by(code=code).first():
            flash(f'Ya existe un dispenser con el código "{code}".', 'danger')
            return render_template('dispensers/form.html', dispenser=None, models=MODELS)

        d = Dispenser(code=code, model=model, status='deposito', notes=notes)
        db.session.add(d)
        db.session.commit()
        flash(f'Dispenser "{code}" dado de alta. Está en depósito.', 'success')
        return redirect(url_for('dispensers.index'))

    return render_template('dispensers/form.html', dispenser=None, models=MODELS)


# ── Editar dispenser ───────────────────────────────────────────────────────────

@dispensers_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit(id):
    d = Dispenser.query.get_or_404(id)
    if request.method == 'POST':
        d.model = request.form.get('model', d.model).strip()
        d.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Dispenser actualizado.', 'success')
        return redirect(url_for('dispensers.detail', id=id))
    return render_template('dispensers/form.html', dispenser=d, models=MODELS)


# ── Detalle e historial ────────────────────────────────────────────────────────

@dispensers_bp.route('/<int:id>')
@login_required
def detail(id):
    d = Dispenser.query.get_or_404(id)
    vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()
    # Clientes conocidos (texto libre ya usado, sin duplicados)
    known_clients = db.session.query(DispenserMovement.client_name)\
        .filter(DispenserMovement.client_name.isnot(None),
                DispenserMovement.client_name != '')\
        .distinct().order_by(DispenserMovement.client_name).all()
    known_clients = [r[0] for r in known_clients]
    return render_template('dispensers/detail.html', dispenser=d,
                           vehicles=vehicles, known_clients=known_clients)


# ── Registrar movimiento (por código) ─────────────────────────────────────────

@dispensers_bp.route('/<int:id>/movimiento', methods=['POST'])
@login_required
def add_movement(id):
    d = Dispenser.query.get_or_404(id)
    movement_type = request.form.get('movement_type', '')
    date_str = request.form.get('date') or str(date.today())
    vehicle_id = request.form.get('vehicle_id') or None
    client_name = request.form.get('client_name', '').strip()
    notes = request.form.get('notes', '').strip()

    if movement_type not in ('salida', 'entrada', 'taller'):
        flash('Tipo de movimiento inválido.', 'danger')
        return redirect(url_for('dispensers.detail', id=id))

    mov_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    m = DispenserMovement(
        dispenser_id=d.id,
        date=mov_date,
        movement_type=movement_type,
        vehicle_id=int(vehicle_id) if vehicle_id else None,
        client_name=client_name,
        notes=notes,
        user_id=current_user.id,
    )
    db.session.add(m)

    # Actualizar estado del dispenser
    if movement_type == 'salida':
        d.status = 'campo'
        d.current_client = client_name
        d.current_vehicle_id = int(vehicle_id) if vehicle_id else None
    elif movement_type == 'entrada':
        d.status = 'deposito'
        d.current_client = None
        d.current_vehicle_id = None
    elif movement_type == 'taller':
        d.status = 'taller'
        d.current_client = None
        d.current_vehicle_id = None

    db.session.commit()
    flash(f'Movimiento registrado: {m.type_label} — {d.code}.', 'success')
    return redirect(url_for('dispensers.detail', id=id))


# ── Movimiento por volumen (usa sistema de stock de productos) ─────────────────

@dispensers_bp.route('/volumen/movimiento', methods=['POST'])
@login_required
def vol_movement():
    product_id = request.form.get('product_id', '')
    quantity_str = request.form.get('quantity', '')
    direction = request.form.get('direction', 'salida')
    date_str = request.form.get('date') or str(date.today())
    vehicle_id = request.form.get('vehicle_id') or None
    client_name = request.form.get('client_name', '').strip()
    notes = request.form.get('notes', '').strip()

    if not product_id or not quantity_str:
        flash('Producto y cantidad son obligatorios.', 'danger')
        return redirect(url_for('dispensers.index', mode='volumen'))

    product = Product.query.get_or_404(int(product_id))
    qty = int(quantity_str)
    mov_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    movement_type = 'distribucion_salida' if direction == 'salida' else 'devolucion_lleno'
    note_text = notes or f'Dispenser {direction} — {client_name or "sin cliente"}'

    update_stock(
        product=product,
        quantity=qty,
        direction=direction,
        movement_type=movement_type,
        notes=note_text,
        user_id=current_user.id,
        date=mov_date,
    )
    db.session.commit()

    accion = 'enviado al campo' if direction == 'salida' else 'retornado al depósito'
    flash(f'{qty} x {product.name} {accion}.', 'success')
    return redirect(url_for('dispensers.index', mode='volumen'))


# ── Desactivar dispenser ───────────────────────────────────────────────────────

@dispensers_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('Sin permisos para dar de baja dispensers.', 'danger')
        return redirect(url_for('dispensers.index'))
    d = Dispenser.query.get_or_404(id)
    d.active = False
    db.session.commit()
    flash(f'Dispenser "{d.code}" dado de baja.', 'info')
    return redirect(url_for('dispensers.index'))
