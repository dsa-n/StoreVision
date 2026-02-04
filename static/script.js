let sessionId = localStorage.getItem('sessionId');
let usuario = JSON.parse(localStorage.getItem('usuario') || 'null');

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', function() {
    verificarAutenticacion();
    
    // Configurar formulario de login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function verificarAutenticacion() {
    if (sessionId && usuario) {
        mostrarInterfazAutenticada();
        await cargarDashboard();
    } else {
        mostrarInterfazLogin();
    }
}

function mostrarInterfazLogin() {
    const loginSection = document.getElementById('loginSection');
    const dashboardContent = document.getElementById('dashboardContent');
    const userInfo = document.getElementById('userInfo');
    
    if (loginSection) loginSection.style.display = 'block';
    if (dashboardContent) dashboardContent.style.display = 'none';
    if (userInfo) {
        userInfo.querySelector('#userName').textContent = 'No autenticado';
    }
}

function mostrarInterfazAutenticada() {
    const loginSection = document.getElementById('loginSection');
    const dashboardContent = document.getElementById('dashboardContent');
    const userInfo = document.getElementById('userInfo');
    
    if (loginSection) loginSection.style.display = 'none';
    if (dashboardContent) dashboardContent.style.display = 'block';
    if (userInfo && usuario) {
        userInfo.querySelector('#userName').textContent = `${usuario.nombre} (${usuario.rol})`;
    }
}

async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            sessionId = data.session_id;
            usuario = data.usuario;
            
            localStorage.setItem('sessionId', sessionId);
            localStorage.setItem('usuario', JSON.stringify(usuario));
            
            mostrarInterfazAutenticada();
            await cargarDashboard();
            
            mostrarMensaje('Login exitoso', 'success');
        } else {
            const error = await response.json();
            mostrarMensaje(error.detail || 'Error en login', 'error');
        }
    } catch (error) {
        mostrarMensaje('Error de conexión', 'error');
    }
}

async function cargarDashboard() {
    try {
        // Cargar consolidado de ventas
        const responseVentas = await fetch('/api/ventas/consolidado', {
            headers: {
                'session-id': sessionId
            }
        });
        
        if (responseVentas.ok) {
            const consolidado = await responseVentas.json();
            document.getElementById('ventasHoy').textContent = consolidado.total_ventas || 0;
            document.getElementById('montoHoy').textContent = `$${(consolidado.monto_total || 0).toFixed(2)}`;
        }
        
        // Cargar alertas de inventario
        const responseAlertas = await fetch('/api/inventario/alertas', {
            headers: {
                'session-id': sessionId
            }
        });
        
        if (responseAlertas.ok) {
            const alertas = await responseAlertas.json();
            document.getElementById('alertasInventario').textContent = alertas.length || 0;
            
            // Mostrar alertas si existen
            if (alertas.length > 0 && Array.isArray(alertas)) {
                mostrarAlertasInventario(alertas);
            }
        }
        
        // Cargar productos más vendidos
        const responseProductos = await fetch('/api/reportes/productos-mas-vendidos', {
            headers: {
                'session-id': sessionId
            }
        });
        
        if (responseProductos.ok) {
            const productos = await responseProductos.json();
            mostrarTopProductos(productos);
        }
        
    } catch (error) {
        console.error('Error cargando dashboard:', error);
    }
}

function mostrarAlertasInventario(alertas) {
    const alertasContainer = document.getElementById('alertasContainer') || crearSeccionAlertas();
    
    alertasContainer.innerHTML = '';
    
    alertas.forEach(alerta => {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning';
        alertDiv.innerHTML = `
            <strong>${alerta.nombre}</strong> - 
            Stock actual: ${alerta.stock_actual} (Mínimo: ${alerta.stock_minimo})
        `;
        alertasContainer.appendChild(alertDiv);
    });
}

function crearSeccionAlertas() {
    const dashboard = document.querySelector('.dashboard-content');
    const alertasSection = document.createElement('div');
    alertasSection.id = 'alertasSection';
    alertasSection.innerHTML = '<h3>Alertas de Inventario</h3><div id="alertasContainer"></div>';
    dashboard.appendChild(alertasSection);
    return document.getElementById('alertasContainer');
}

function mostrarTopProductos(productos) {
    const container = document.getElementById('topProductos');
    
    if (productos.error) {
        container.innerHTML = `
            <div class="sin-datos">
                <i>🏆</i>
                <h4>No hay datos de productos</h4>
                <p>${productos.error}</p>
            </div>
        `;
        return;
    }
    
    if (!productos || productos.length === 0) {
        container.innerHTML = `
            <div class="sin-datos">
                <i>📦</i>
                <h4>Sin ventas registradas</h4>
                <p>No hay productos vendidos en el periodo seleccionado</p>
                <small>Cuando realice ventas, aquí aparecerán los productos más populares</small>
            </div>
        `;
        return;
    }
    
    // Filtrar productos que realmente tengan ventas
    const productosConVentas = productos.filter(prod => (prod.total_vendido || 0) > 0);
    
    if (productosConVentas.length === 0) {
        container.innerHTML = `
            <div class="sin-datos">
                <i>📊</i>
                <h4>Sin productos vendidos</h4>
                <p>No hay productos con ventas en el periodo seleccionado</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="productos-ranking">
            <div class="ranking-header">
                <span>#</span>
                <span>Producto</span>
                <span>Unidades Vendidas</span>
                <span>Total Ingresos</span>
            </div>
    `;
    
    productosConVentas.slice(0, 10).forEach((prod, index) => {
        const totalVendido = prod.total_vendido || 0;
        const totalIngresos = prod.total_ingresos || 0;
        
        html += `
            <div class="producto-ranking">
                <div class="ranking-posicion">${index + 1}</div>
                <div class="ranking-info">
                    <strong>${prod.nombre}</strong>
                    <div class="producto-detalle">
                        <small>Código: ${prod.codigo} | Categoría: ${prod.categoria}</small>
                    </div>
                </div>
                <div class="ranking-cantidad">
                    ${totalVendido} unidades
                </div>
                <div class="ranking-ingresos">
                    $${totalIngresos.toFixed(2)}
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    
    // Resumen total
    const totalUnidades = productosConVentas.reduce((sum, prod) => sum + (prod.total_vendido || 0), 0);
    const totalIngresos = productosConVentas.reduce((sum, prod) => sum + (prod.total_ingresos || 0), 0);
    
    html += `
        <div class="resumen-productos">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <strong>Total Unidades Vendidas:</strong> ${totalUnidades}
                </div>
                <div>
                    <strong>Total Ingresos:</strong> $${totalIngresos.toFixed(2)}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}
function mostrarMensaje(mensaje, tipo) {
    // Implementar sistema de notificaciones
    alert(mensaje); // Simplificado para el ejemplo
}

function logout() {
    sessionId = null;
    usuario = null;
    localStorage.removeItem('sessionId');
    localStorage.removeItem('usuario');
    mostrarInterfazLogin();
    mostrarMensaje('Sesión cerrada', 'success');
}

// Funciones para el módulo de ventas
async function registrarVenta(datosVenta) {
    try {
        const response = await fetch('/api/ventas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'session-id': sessionId
            },
            body: JSON.stringify(datosVenta)
        });
        
        if (response.ok) {
            const resultado = await response.json();
            mostrarMensaje('Venta registrada exitosamente', 'success');
            return resultado;
        } else {
            const error = await response.json();
            mostrarMensaje(error.detail || 'Error registrando venta', 'error');
            return null;
        }
    } catch (error) {
        mostrarMensaje('Error de conexión', 'error');
        return null;
    }
}