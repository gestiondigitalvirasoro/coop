from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import func
from models import db, Product, Category, Distribution, DistributionItem, ProductionRecord, PlantSale, Breakage, StockMovement

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    products = (Product.query
                .filter_by(active=True)
                .order_by(Product.category_id, Product.name).all())
    categories = Category.query.order_by(Category.name).all()

    active_dists = Distribution.query.filter_by(status='salida').all()
    pending_returnables = []
    for dist in active_dists:
        for item in dist.items:
            if item.product.is_returnable:
                pending = item.qty_sent - item.qty_returned_full - item.qty_returned_empty
                if pending > 0:
                    pending_returnables.append({
                        'vehicle': dist.vehicle.code,
                        'driver': dist.driver.name,
                        'date': dist.date,
                        'dist_id': dist.id,
                        'product': item.product.name,
                        'sent': item.qty_sent,
                        'returned_full': item.qty_returned_full,
                        'returned_empty': item.qty_returned_empty,
                        'pending': pending,
                    })

    today = date.today()
    month_start = today.replace(day=1)

    today_production = db.session.query(func.sum(ProductionRecord.quantity)).filter(
        ProductionRecord.date == today
    ).scalar() or 0

    month_production = db.session.query(func.sum(ProductionRecord.quantity)).filter(
        ProductionRecord.date >= month_start
    ).scalar() or 0

    month_sales = db.session.query(func.sum(PlantSale.quantity)).filter(
        PlantSale.date >= month_start
    ).scalar() or 0

    month_breakage = db.session.query(func.sum(Breakage.quantity)).filter(
        Breakage.date >= month_start
    ).scalar() or 0

    return render_template('reports/index.html',
                           products=products,
                           categories=categories,
                           pending_returnables=pending_returnables,
                           today_production=today_production,
                           month_production=month_production,
                           month_sales=month_sales,
                           month_breakage=month_breakage,
                           today=today)


@reports_bp.route('/movimientos')
@login_required
def movements():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    product_id = request.args.get('product_id', '')
    movement_type = request.args.get('movement_type', '')

    query = StockMovement.query.order_by(
        StockMovement.date.desc(), StockMovement.created_at.desc()
    )

    if date_from:
        query = query.filter(StockMovement.date >= date_from)
    if date_to:
        query = query.filter(StockMovement.date <= date_to)
    if product_id:
        query = query.filter(StockMovement.product_id == int(product_id))
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)

    movements_list = query.limit(500).all()
    products = Product.query.filter_by(active=True).order_by(Product.name).all()

    return render_template('reports/movements.html',
                           movements=movements_list,
                           products=products,
                           date_from=date_from,
                           date_to=date_to,
                           product_filter=product_id,
                           movement_type_filter=movement_type,
                           movement_types=StockMovement.MOVEMENT_LABELS)


@reports_bp.route('/api/chart-data')
@login_required
def chart_data():
    today = date.today()
    days = int(request.args.get('days', 7))
    days = min(max(days, 7), 30)

    labels = []
    production_data = []
    sales_data = []
    breakage_data = []

    for i in range(days - 1, -1, -1):
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

        brk = db.session.query(func.sum(Breakage.quantity)).filter(
            Breakage.date == day
        ).scalar() or 0
        breakage_data.append(brk)

    categories = Category.query.all()
    cat_labels = [c.name for c in categories]
    cat_data = [sum(p.stock for p in c.products if p.active) for c in categories]

    top_products = (db.session.query(
        Product.name,
        func.sum(DistributionItem.qty_sent).label('total')
    ).join(DistributionItem, Product.id == DistributionItem.product_id)
     .join(Distribution, Distribution.id == DistributionItem.distribution_id)
     .filter(Distribution.date >= today - timedelta(days=30))
     .group_by(Product.id)
     .order_by(func.sum(DistributionItem.qty_sent).desc())
     .limit(5).all())

    return jsonify({
        'trend': {
            'labels': labels,
            'production': production_data,
            'sales': sales_data,
            'breakage': breakage_data,
        },
        'stock_by_category': {
            'labels': cat_labels,
            'data': cat_data,
        },
        'top_products': {
            'labels': [r.name for r in top_products],
            'data': [r.total for r in top_products],
        },
    })
