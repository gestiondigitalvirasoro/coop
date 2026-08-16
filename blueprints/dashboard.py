from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from models import db, Product, Category, Distribution, ProductionRecord, PlantSale, StockMovement, Vehicle, Dispenser

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)

    total_products = Product.query.filter_by(active=True).count()

    low_stock_count = Product.query.filter(
        Product.active == True,
        Product.min_stock > 0,
        Product.stock <= Product.min_stock
    ).count()

    pending_distributions = Distribution.query.filter_by(status='salida').count()

    today_production = db.session.query(func.sum(ProductionRecord.quantity)).filter(
        ProductionRecord.date == today
    ).scalar() or 0

    month_production = db.session.query(func.sum(ProductionRecord.quantity)).filter(
        ProductionRecord.date >= month_start
    ).scalar() or 0

    today_sales = db.session.query(func.sum(PlantSale.quantity)).filter(
        PlantSale.date == today
    ).scalar() or 0

    recent_movements = (StockMovement.query
                        .order_by(StockMovement.created_at.desc())
                        .limit(10).all())

    active_distributions = Distribution.query.filter_by(status='salida').all()
    total_pending_returnables = sum(d.pending_returnables for d in active_distributions)

    low_stock_products = Product.query.filter(
        Product.active == True,
        Product.min_stock > 0,
        Product.stock <= Product.min_stock
    ).order_by(Product.stock.asc()).limit(5).all()

    today_distributions = (Distribution.query
                           .filter_by(date=today)
                           .order_by(Distribution.created_at.desc()).all())

    # ── Panel inicio del día ───────────────────────────────────────────────────
    production_done_today = today_production > 0

    # Vehículos activos que NO tienen distribución hoy
    all_vehicles = Vehicle.query.filter_by(active=True).order_by(Vehicle.code).all()
    dispatched_today_ids = {d.vehicle_id for d in today_distributions}
    vehicles_not_dispatched = [v for v in all_vehicles if v.id not in dispatched_today_ids]

    # Distribuciones en ruta (sin retorno), con su fecha
    pending_returns = (Distribution.query
                       .filter_by(status='salida')
                       .order_by(Distribution.date.asc()).all())
    overdue_returns = [d for d in pending_returns if d.date < today]

    dispensers_taller = Dispenser.query.filter_by(status='taller', active=True).count()

    return render_template('dashboard/index.html',
                           total_products=total_products,
                           low_stock_count=low_stock_count,
                           pending_distributions=pending_distributions,
                           today_production=today_production,
                           month_production=month_production,
                           today_sales=today_sales,
                           recent_movements=recent_movements,
                           total_pending_returnables=total_pending_returnables,
                           low_stock_products=low_stock_products,
                           today_distributions=today_distributions,
                           today=today,
                           production_done_today=production_done_today,
                           vehicles_not_dispatched=vehicles_not_dispatched,
                           pending_returns=pending_returns,
                           overdue_returns=overdue_returns,
                           dispensers_taller=dispensers_taller)


@dashboard_bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    today = date.today()

    labels = []
    production_data = []
    sales_data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%d/%m'))

        prod = db.session.query(func.sum(ProductionRecord.quantity)).filter(
            ProductionRecord.date == day
        ).scalar() or 0
        production_data.append(prod)

        sale = db.session.query(func.sum(PlantSale.quantity)).filter(
            PlantSale.date == day
        ).scalar() or 0
        sales_data.append(sale)

    categories = Category.query.all()
    cat_labels = [c.name for c in categories]
    cat_data = [sum(p.stock for p in c.products if p.active) for c in categories]

    return jsonify({
        'production': {'labels': labels, 'data': production_data},
        'sales': {'labels': labels, 'data': sales_data},
        'stock_by_category': {'labels': cat_labels, 'data': cat_data},
    })
