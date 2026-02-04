from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models.database import obtener_db
from models.modelos import Producto, Venta, ItemVenta, RegistroAuditoria  # Agregar importaciones
from controllers.ventas_controller import ControladorVentas
from controllers.inventario_controller import ControladorInventario
from controllers.auth_controller import ControladorAutenticacion
from controllers.reportes_controller import ControladorReportes  # Agregar esta importación
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Simulación de sesión (en producción usar JWT)
usuarios_activos = {}

# Vistas de la interfaz web
@router.get("/", response_class=HTMLResponse)
async def pagina_principal(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/ventas", response_class=HTMLResponse)
async def pagina_ventas(request: Request):
    return templates.TemplateResponse("ventas.html", {"request": request})

@router.get("/inventario", response_class=HTMLResponse)
async def pagina_inventario(request: Request):
    return templates.TemplateResponse("inventario.html", {"request": request})

@router.get("/reportes", response_class=HTMLResponse)
async def pagina_reportes(request: Request):
    return templates.TemplateResponse("reportes.html", {"request": request})

# API Endpoints
@router.post("/api/login")
async def login(request: Request, db: Session = Depends(obtener_db)):
    datos = await request.json()
    controlador_auth = ControladorAutenticacion(db)
    
    usuario = controlador_auth.autenticar_usuario(
        datos['email'], 
        datos['password'],
        request.client.host
    )
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Simular sesión
    session_id = f"session_{usuario.id}_{datetime.utcnow().timestamp()}"
    usuarios_activos[session_id] = {
        'usuario_id': usuario.id,
        'nombre': usuario.nombre,
        'rol': usuario.rol,
        'email': usuario.email
    }
    
    return {
        "mensaje": "Login exitoso",
        "session_id": session_id,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "email": usuario.email
        }
    }

@router.post("/api/ventas")
async def crear_venta(request: Request, db: Session = Depends(obtener_db)):
    datos = await request.json()
    session_id = request.headers.get('session-id')
    
    if not session_id or session_id not in usuarios_activos:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    usuario = usuarios_activos[session_id]
    controlador_ventas = ControladorVentas(db)
    
    resultado = controlador_ventas.registrar_venta(datos, usuario['usuario_id'])
    
    if 'error' in resultado:
        raise HTTPException(status_code=400, detail=resultado['error'])
    
    return resultado

@router.get("/api/ventas/consolidado")
async def obtener_consolidado_ventas(db: Session = Depends(obtener_db)):
    controlador_ventas = ControladorVentas(db)
    consolidado = controlador_ventas.consolidar_ventas_diarias()
    return consolidado

@router.get("/api/inventario/alertas")
async def obtener_alertas_inventario(db: Session = Depends(obtener_db)):
    controlador_inventario = ControladorInventario(db)
    alertas = controlador_inventario.verificar_alertas_inventario()
    return alertas

@router.get("/api/reportes/productos-mas-vendidos")
async def obtener_productos_mas_vendidos(
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None
        
        productos = controlador_reportes.obtener_productos_mas_vendidos(
            fecha_inicio_dt, fecha_fin_dt
        )
        
        return productos
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo productos más vendidos: {str(e)}")

@router.post("/api/inventario/movimientos")
async def registrar_movimiento_inventario(request: Request, db: Session = Depends(obtener_db)):
    datos = await request.json()
    session_id = request.headers.get('session-id')
    
    if not session_id or session_id not in usuarios_activos:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    usuario = usuarios_activos[session_id]
    controlador_inventario = ControladorInventario(db)
    
    resultado = controlador_inventario.registrar_movimiento(datos, usuario['usuario_id'])
    
    if 'error' in resultado:
        raise HTTPException(status_code=400, detail=resultado['error'])
    
    return resultado

@router.get("/api/inventario/productos")
async def obtener_productos_inventario(db: Session = Depends(obtener_db)):
    try:
        productos = db.query(Producto).filter(Producto.activo == True).all()
        return [
            {
                "id": p.id,
                "codigo": p.codigo,
                "nombre": p.nombre,
                "categoria": p.categoria,
                "stock_actual": p.stock_actual,
                "stock_minimo": p.stock_minimo,
                "precio_venta": p.precio_venta
            }
            for p in productos
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo productos: {str(e)}")

@router.get("/api/inventario/historial")
async def obtener_historial_inventario(
    producto_id: int = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_inventario = ControladorInventario(db)
        
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None
        
        historial = controlador_inventario.obtener_historial_movimientos(
            producto_id, fecha_inicio_dt, fecha_fin_dt
        )
        
        if isinstance(historial, dict) and 'error' in historial:
            raise HTTPException(status_code=400, detail=historial['error'])
        
        return [
            {
                "fecha_movimiento": m.fecha_movimiento,
                "producto": {"nombre": m.producto.nombre},
                "tipo_movimiento": m.tipo_movimiento,
                "cantidad": m.cantidad,
                "stock_anterior": m.stock_anterior,
                "stock_nuevo": m.stock_nuevo,
                "motivo": m.motivo,
                "usuario": {"nombre": m.usuario.nombre}
            }
            for m in historial
        ]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo historial: {str(e)}")

@router.get("/api/reportes/balance")
async def obtener_balance_economico(
    fecha_inicio: str,
    fecha_fin: str,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
        fecha_fin_dt = datetime.fromisoformat(fecha_fin)
        
        # Solo una sucursal, no necesita parámetro
        balance = controlador_reportes.generar_balance_economico(
            fecha_inicio_dt, fecha_fin_dt
        )
        
        return balance
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generando balance: {str(e)}")

@router.get("/api/reportes/indicadores-ventas")
async def obtener_indicadores_ventas(
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_reportes = ControladorReportes(db)
        
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None
        
        indicadores = controlador_reportes.obtener_indicadores_ventas(
            fecha_inicio_dt, fecha_fin_dt
        )
        
        return indicadores
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo indicadores: {str(e)}")

@router.get("/api/ventas")
async def obtener_ventas(
    fecha: str = None,
    db: Session = Depends(obtener_db)
):
    try:
        controlador_ventas = ControladorVentas(db)
        
        if fecha:
            fecha_inicio = datetime.fromisoformat(fecha)
            fecha_fin = fecha_inicio.replace(hour=23, minute=59, second=59)
        else:
            fecha_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0)
            fecha_fin = datetime.utcnow().replace(hour=23, minute=59, second=59)
        
        ventas = controlador_ventas.obtener_ventas_por_periodo(
            fecha_inicio, fecha_fin
        )
        
        if isinstance(ventas, dict) and 'error' in ventas:
            raise HTTPException(status_code=400, detail=ventas['error'])
        
        return [
            {
                "id": v.id,
                "fecha_venta": v.fecha_venta,
                "total": v.total,
                "usuario": {"nombre": v.usuario.nombre},
                "items": [
                    {
                        "cantidad": i.cantidad,
                        "producto": {"nombre": i.producto.nombre},
                        "precio_unitario": i.precio_unitario,
                        "subtotal": i.subtotal
                    }
                    for i in v.items
                ]
            }
            for v in ventas
        ]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo ventas: {str(e)}")
    
@router.post("/api/ventas/{venta_id}/anular")
async def anular_venta(
    venta_id: int,
    request: Request,
    db: Session = Depends(obtener_db)
):
    try:
        datos = await request.json()
        session_id = request.headers.get('session-id')
        
        if not session_id or session_id not in usuarios_activos:
            raise HTTPException(status_code=401, detail="No autenticado")
        
        usuario = usuarios_activos[session_id]
        
        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para anular ventas")
        
        controlador_ventas = ControladorVentas(db)
        resultado = controlador_ventas.anular_venta(
            venta_id, usuario['usuario_id'], datos.get('motivo', 'Sin motivo especificado')
        )
        
        if 'error' in resultado:
            raise HTTPException(status_code=400, detail=resultado['error'])
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error anulando venta: {str(e)}")

@router.get("/api/productos")
async def obtener_productos(db: Session = Depends(obtener_db)):
    try:
        productos = db.query(Producto).filter(Producto.activo == True).all()
        return [
            {
                "id": p.id,
                "nombre": p.nombre,
                "precio_venta": p.precio_venta,
                "stock_actual": p.stock_actual,
                "categoria": p.categoria,
                "codigo": p.codigo
            }
            for p in productos
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo productos: {str(e)}")
    
@router.post("/api/inventario/productos")
async def crear_producto(request: Request, db: Session = Depends(obtener_db)):
    try:
        datos = await request.json()
        session_id = request.headers.get('session-id')
        
        if not session_id or session_id not in usuarios_activos:
            raise HTTPException(status_code=401, detail="No autenticado")
        
        usuario = usuarios_activos[session_id]
        
        # Verificar permisos (solo administradora puede crear productos)
        if usuario['rol'] != 'administradora':
            raise HTTPException(status_code=403, detail="No tiene permisos para crear productos")
        
        # Verificar si el código ya existe
        producto_existente = db.query(Producto).filter(Producto.codigo == datos['codigo']).first()
        if producto_existente:
            raise HTTPException(status_code=400, detail="El código del producto ya existe")
        
        nuevo_producto = Producto(
            codigo=datos['codigo'],
            nombre=datos['nombre'],
            categoria=datos['categoria'],
            precio_venta=datos['precio_venta'],
            costo=datos['costo'],
            stock_actual=datos.get('stock_actual', 0),
            stock_minimo=datos.get('stock_minimo', 5),
            descripcion=datos.get('descripcion', '')
        )
        
        db.add(nuevo_producto)
        
        # Registrar en auditoría
        auditoria = RegistroAuditoria(
            usuario_id=usuario['usuario_id'],
            tipo_accion="creacion_producto",
            descripcion=f"Producto creado: {datos['nombre']} ({datos['codigo']})",
            fecha_accion=datetime.utcnow()
        )
        db.add(auditoria)
        
        db.commit()
        
        return {"mensaje": "Producto creado exitosamente", "producto_id": nuevo_producto.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando producto: {str(e)}")
    


@router.get("/api/debug/ventas")
async def debug_ventas(db: Session = Depends(obtener_db)):
    """Endpoint temporal para debug de ventas"""
    try:
        # Verificar si hay ventas
        ventas_count = db.query(Venta).count()
        ventas_completadas = db.query(Venta).filter(Venta.estado == 'completada').count()
        
        # Verificar items de venta
        items_count = db.query(ItemVenta).count()
        
        # Verificar productos
        productos_count = db.query(Producto).count()
        
        # Algunas ventas recientes con sus items
        ventas_recientes = db.query(Venta).filter(Venta.estado == 'completada').order_by(Venta.fecha_venta.desc()).limit(5).all()
        
        ventas_detalle = []
        for venta in ventas_recientes:
            items = db.query(ItemVenta).filter(ItemVenta.venta_id == venta.id).all()
            ventas_detalle.append({
                'venta_id': venta.id,
                'fecha': venta.fecha_venta,
                'total': venta.total,
                'items_count': len(items),
                'items': [{'producto_id': i.producto_id, 'cantidad': i.cantidad} for i in items]
            })
        
        return {
            'estadisticas': {
                'total_ventas': ventas_count,
                'ventas_completadas': ventas_completadas,
                'total_items_venta': items_count,
                'total_productos': productos_count
            },
            'ventas_recientes': ventas_detalle
        }
        
    except Exception as e:
        return {"error": str(e)}
