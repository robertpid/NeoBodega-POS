// ==========================================
// ECOSISTEMA POS - FRONTEND LOGIC (VANILLA JS)
// ==========================================

const API_URL = 'http://localhost:8000/api/v1';

// 1. GESTIÓN DE SESIÓN Y SEGURIDAD
const token = localStorage.getItem('pos_token');

// Redirección inmediata si no hay token (Protección de rutas frontend)
if (!token) {
    window.location.href = 'login.html';
}

function logout() {
    localStorage.removeItem('pos_token');
    window.location.href = 'login.html';
}

// 2. SISTEMA DE NOTIFICACIONES (TOASTS)
function showToast(msg, isError = false) {
    const toast = document.getElementById('toast');
    document.getElementById('toastMsg').innerText = msg;
    document.getElementById('toastIcon').innerText = isError ? '❌' : '✅';
    
    // Feedback visual usando colores Tailwind
    toast.style.backgroundColor = isError ? '#ef4444' : '#1e293b';
    toast.style.transform = 'translateY(0)';
    toast.style.opacity = '1';
    
    // Auto ocultar
    setTimeout(() => {
        toast.style.transform = 'translateY(24px)';
        toast.style.opacity = '0';
    }, 4000);
}

// 3. ENRUTAMIENTO SPA (SINGLE PAGE APPLICATION)
function navigate(viewId) {
    // A. Actualizar estado visual del menú lateral
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('bg-indigo-600/10', 'text-indigo-400');
        btn.classList.add('hover:bg-white/5');
    });
    const clickedBtn = event.currentTarget;
    clickedBtn.classList.remove('hover:bg-white/5');
    clickedBtn.classList.add('bg-indigo-600/10', 'text-indigo-400');

    // B. Transición de Vistas
    document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
    });
    const targetView = document.getElementById(`view-${viewId}`);
    targetView.classList.add('active');

    // C. Actualizar Cabecera
    const titles = {
        'dashboard': 'Visión General',
        'pos': 'Terminal Punto de Venta',
        'inventory': 'Catálogo de Inventario',
        'users': 'Gestión de Personal',
        'crm': 'Supervisión de Inteligencia Artificial (HITL)'
    };
    document.getElementById('page-title').innerText = titles[viewId];

    // D. Disparar lógica de negocio según la vista
    if (viewId === 'dashboard') loadDashboardData();
    if (viewId === 'users') loadUsers();
    if (viewId === 'inventory') loadInventory();
    
    // Auto-focus barcode scanner if POS
    if (viewId === 'pos') {
        loadInventory(); // Ensures bulk products are rendered
        setTimeout(() => document.getElementById('barcodeInput').focus(), 100);
    }
}

// 4. LÓGICA DEL DASHBOARD
let salesChartInstance = null;

async function loadDashboardData() {
    try {
        // Fetch: Cierre de Caja (Agrupación SQL rápida)
        const posRes = await fetch(`${API_URL}/pos/cierre-caja`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (posRes.ok) {
            const data = await posRes.json();
            // Formateo de moneda
            document.getElementById('metric-income').innerHTML = `<span class="text-2xl text-slate-400">S/</span> ${data.Total_Dia.toFixed(2)}`;
        }

        // Fetch: HITL CRM Bandeja
        const crmRes = await fetch(`${API_URL}/crm/mensajes/pendientes`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (crmRes.ok) {
            const crmData = await crmRes.json();
            document.getElementById('metric-crm').innerText = crmData.length;
        } else if(crmRes.status === 401 || crmRes.status === 403) {
            // El token caducó o el usuario no es admin
            showToast("Tu sesión ha expirado o no tienes permisos", true);
            if(crmRes.status === 401) logout();
        }

        // Renderizar el gráfico
        renderChart();
        
    } catch (error) {
        console.error("Fallo al conectar con FastAPI:", error);
    }
}

function renderChart() {
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    // Prevenir fugas de memoria destruyendo la instancia anterior
    if(salesChartInstance) salesChartInstance.destroy();
    
    // Gradiente dinámico para el área bajo la curva
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.2)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

    salesChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Ingresos Históricos',
                data: [420, 380, 510, 490, 850, 1100, 950],
                borderColor: '#4f46e5', // indigo-600
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#4f46e5',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.4, // Curvas suaves
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 12,
                    titleFont: { family: 'Inter', size: 14 },
                    bodyFont: { family: 'Inter', size: 13 },
                    displayColors: false
                }
            },
            scales: { 
                y: { 
                    beginAtZero: true, 
                    grid: { color: '#f1f5f9', borderDash: [5, 5] },
                    border: { display: false }
                }, 
                x: { 
                    grid: { display: false },
                    border: { display: false }
                } 
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        }
    });
}

// 5. GESTIÓN DE USUARIOS (CRUD)
async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/users/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const users = await response.json();
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = ''; // Limpiar tabla
            
            users.forEach(user => {
                // Estilo condicional según el Rol (Badges)
                const roleBadge = user.role === 'admin' 
                    ? '<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-bold px-3 py-1 rounded-lg tracking-wide uppercase">Admin</span>'
                    : '<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold px-3 py-1 rounded-lg tracking-wide uppercase">Cajero</span>';
                
                tbody.innerHTML += `
                    <tr class="hover:bg-slate-50 transition-colors group">
                        <td class="p-5 text-slate-400 font-medium">#${user.id}</td>
                        <td class="p-5 font-bold text-slate-700">${user.username}</td>
                        <td class="p-5">${roleBadge}</td>
                        <td class="p-5 text-right">
                            <button onclick="deleteUser(${user.id})" class="text-red-400 hover:text-red-600 bg-white hover:bg-red-50 border border-slate-200 hover:border-red-200 px-4 py-1.5 rounded-lg transition-all font-medium text-sm shadow-sm opacity-50 group-hover:opacity-100">
                                Eliminar
                            </button>
                        </td>
                    </tr>
                `;
            });
        }
    } catch (e) {
        showToast("No se pudo conectar a la API", true);
    }
}

// Control del Modal
function openUserModal() {
    const modal = document.getElementById('userModal');
    modal.classList.remove('hidden');
    // Pequeño delay para permitir que el display block se aplique antes de animar opacidad
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('userModalContent').classList.remove('scale-95');
    }, 10);
}

function closeUserModal() {
    const modal = document.getElementById('userModal');
    modal.classList.add('opacity-0');
    document.getElementById('userModalContent').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
        document.getElementById('addUserForm').reset();
    }, 300);
}

// Acción: Crear Usuario (POST)
document.getElementById('addUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const payload = {
        username: document.getElementById('newUsername').value,
        password: document.getElementById('newPassword').value,
        role: document.getElementById('newRole').value
    };

    try {
        const response = await fetch(`${API_URL}/users/`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showToast("Personal autorizado registrado con éxito");
            closeUserModal();
            loadUsers(); // Recargar la tabla dinámicamente
        } else {
            const err = await response.json();
            showToast(err.detail, true);
        }
    } catch (error) {
        showToast("Error de red conectando al servidor", true);
    }
});

// Acción: Eliminar Usuario (DELETE)
async function deleteUser(id) {
    if(!confirm("¿CONFIRMACIÓN DE SEGURIDAD:\n¿Estás completamente seguro de revocar el acceso a este usuario?")) return;
    
    try {
        const response = await fetch(`${API_URL}/users/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if(response.ok) {
            showToast("Acceso revocado y usuario eliminado");
            loadUsers(); // Re-renderizar UI
        } else {
            const err = await response.json();
            showToast(err.detail, true);
        }
    } catch (e) {
        showToast("Error de red al intentar eliminar", true);
    }
}

// 6. GESTIÓN DE INVENTARIO
async function loadInventory() {
    try {
        const response = await fetch(`${API_URL}/inventory/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const products = await response.json();
            const tbody = document.getElementById('inventory-table-body');
            tbody.innerHTML = ''; 
            
            // Limpiar productos a granel para el POS
            const bulkContainer = document.getElementById('bulk-products-container');
            if (bulkContainer) bulkContainer.innerHTML = '';
            
            products.forEach(p => {
                if (p.is_bulk && bulkContainer) {
                    bulkContainer.innerHTML += `
                        <button onclick="addBulkItem('${p.name.replace(/'/g, "\\'")}', ${p.price}, '⚖️')" class="p-6 bg-white rounded-3xl shadow-sm border border-slate-100 hover:shadow-xl hover:scale-105 transition-all text-center group flex flex-col items-center justify-center h-full">
                            <div class="text-4xl mb-4 transform group-hover:scale-110 transition-transform">⚖️</div>
                            <div class="font-bold text-slate-700 leading-tight">${p.name}</div>
                            <div class="text-emerald-500 font-bold mt-2 text-sm">S/ ${p.price.toFixed(2)} /Kg</div>
                        </button>
                    `;
                }

                // Simulación del Cold Start del ML: Si stock < 10, advertir compra.
                let suggestion = "";
                if(p.stock <= 5) suggestion = '<span class="text-red-500 font-bold">⚠️ Comprar urgente</span>';
                else if(p.stock <= 15) suggestion = '<span class="text-amber-500 font-semibold">Reabastecer pronto</span>';
                else suggestion = '<span class="text-emerald-500">Stock saludable</span>';

                tbody.innerHTML += `
                    <tr class="hover:bg-slate-50 transition-colors group">
                        <td class="p-5 font-bold text-slate-700 flex items-center space-x-3">
                            <div class="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-xl shadow-sm">📦</div>
                            <span>${p.name}</span>
                        </td>
                        <td class="p-5 text-slate-400 font-mono text-sm">${p.barcode}</td>
                        <td class="p-5 text-center text-lg font-bold ${p.stock < 10 ? 'text-red-500' : 'text-slate-700'}">${p.stock}</td>
                        <td class="p-5 text-slate-700 font-medium">S/ ${p.price.toFixed(2)}</td>
                        <td class="p-5 text-sm">${suggestion}</td>
                        <td class="p-5 text-center">
                            <button onclick="openEditProductModal(${p.id}, '${p.name.replace(/'/g, "\\'")}', ${p.price}, ${p.stock})" class="text-amber-500 hover:text-amber-700 font-bold bg-amber-50 px-3 py-2 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity">✎ Editar</button>
                        </td>
                    </tr>
                `;
            });
        }
    } catch (e) {
        showToast("Error cargando inventario", true);
    }
}

// Modal Inventario
function openProductModal() {
    const modal = document.getElementById('productModal');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('productModalContent').classList.remove('scale-95');
    }, 10);
}

function closeProductModal() {
    const modal = document.getElementById('productModal');
    modal.classList.add('opacity-0');
    document.getElementById('productModalContent').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
        document.getElementById('addProductForm').reset();
        toggleProductType(); // Reset UI
    }, 300);
}

function toggleProductType() {
    const type = document.querySelector('input[name="prodType"]:checked').value;
    const barcodeContainer = document.getElementById('barcodeContainer');
    const barcodeInput = document.getElementById('prodBarcode');
    if (type === 'bulk') {
        barcodeContainer.style.display = 'none';
        barcodeInput.removeAttribute('required');
    } else {
        barcodeContainer.style.display = 'block';
        barcodeInput.setAttribute('required', 'true');
    }
}

document.getElementById('addProductForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const type = document.querySelector('input[name="prodType"]:checked').value;
    const isBulk = type === 'bulk';
    let barcodeVal = document.getElementById('prodBarcode').value;
    
    if (isBulk) {
        // Generar un código de barras interno pseudo-aleatorio para productos a granel
        barcodeVal = "BULK-" + Math.floor(Math.random() * 1000000);
    }

    const payload = {
        barcode: barcodeVal,
        name: document.getElementById('prodName').value,
        price: parseFloat(document.getElementById('prodPrice').value),
        stock: parseFloat(document.getElementById('prodStock').value),
        image_local_path: "",
        requires_price_setup: false,
        is_bulk: isBulk
    };

    try {
        const response = await fetch(`${API_URL}/inventory/`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showToast("Producto agregado exitosamente");
            closeProductModal();
            loadInventory();
        } else {
            const err = await response.json();
            showToast(err.detail, true);
        }
    } catch (error) {
        showToast("Error de red conectando al servidor", true);
    }
});
// Modal de Edición de Producto
function openEditProductModal(id, name, price, stock) {
    document.getElementById('editProdId').value = id;
    document.getElementById('editProdName').value = name;
    document.getElementById('editProdPrice').value = price;
    document.getElementById('editProdStock').value = stock;

    const modal = document.getElementById('editProductModal');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('editProductModalContent').classList.remove('scale-95');
    }, 10);
}

function closeEditProductModal() {
    const modal = document.getElementById('editProductModal');
    modal.classList.add('opacity-0');
    document.getElementById('editProductModalContent').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

// Editar Producto API
document.getElementById('editProductForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('editProdId').value;
    const price = parseFloat(document.getElementById('editProdPrice').value);
    const stock = parseFloat(document.getElementById('editProdStock').value);

    try {
        const response = await fetch(`${API_URL}/inventory/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ price, stock })
        });

        if (response.ok) {
            showToast("Producto actualizado exitosamente");
            closeEditProductModal();
            loadInventory();
        } else {
            const err = await response.json();
            showToast(err.detail || "Error al actualizar producto", true);
        }
    } catch (e) {
        showToast("Error de conexión", true);
    }
});

// 7. LÓGICA DE CAJA Y PUNTO DE VENTA (POS)
let cart = [];

function updateCartUI() {
    const container = document.getElementById('cart-items');
    container.innerHTML = '';
    let total = 0;

    cart.forEach((item, index) => {
        const subtotal = item.price * item.qty;
        total += subtotal;
        
        container.innerHTML += `
            <div class="bg-white p-3 rounded-lg shadow-sm border border-slate-100 flex justify-between items-center group">
                <div class="flex-1">
                    <p class="font-bold text-slate-700 text-sm leading-tight">${item.name}</p>
                    <p class="text-xs text-slate-400 mt-0.5">S/ ${item.price.toFixed(2)} x ${item.qty}</p>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="font-bold text-indigo-600">S/ ${subtotal.toFixed(2)}</span>
                    <button onclick="removeFromCart(${index})" class="text-red-400 hover:text-red-600 bg-red-50 w-6 h-6 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">✕</button>
                </div>
            </div>
        `;
    });

    document.getElementById('cart-subtotal').innerText = `S/ ${total.toFixed(2)}`;
    document.getElementById('cart-total').innerText = `S/ ${total.toFixed(2)}`;
    document.getElementById('checkout-total').innerText = `S/ ${total.toFixed(2)}`;
}

let currentBulkItem = null;

function addBulkItem(name, defaultPrice, icon) {
    currentBulkItem = { name };
    document.getElementById('bulkModalTitle').innerText = name;
    document.getElementById('bulkModalIcon').innerText = icon || '⚖️';
    document.getElementById('bulkPriceInput').value = defaultPrice.toFixed(2);
    document.getElementById('bulkQtyInput').value = '1';
    
    const modal = document.getElementById('bulkModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('bulkModalContent').classList.remove('scale-95');
    }, 10);
}

function changeBulkQty(amount) {
    const input = document.getElementById('bulkQtyInput');
    let val = parseFloat(input.value) || 0;
    val += amount;
    if(val < 0.01) val = 0.01;
    input.value = parseFloat(val.toFixed(3));
}

function closeBulkModal() {
    const modal = document.getElementById('bulkModal');
    modal.classList.add('opacity-0');
    document.getElementById('bulkModalContent').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }, 300);
}

function confirmBulkItem() {
    if(!currentBulkItem) return;
    const qty = parseFloat(document.getElementById('bulkQtyInput').value);
    const price = parseFloat(document.getElementById('bulkPriceInput').value);
    
    if(isNaN(qty) || qty <= 0) {
        showToast("Cantidad inválida", true);
        return;
    }
    if(isNaN(price) || price < 0) {
        showToast("Precio inválido", true);
        return;
    }
    
    cart.push({ id: 999, name: currentBulkItem.name, price: price, qty: qty });
    updateCartUI();
    closeBulkModal();
    document.getElementById('barcodeInput').focus();
}

// Simulador de Escáner Físico (Captura el Enter)
document.getElementById('barcodeInput')?.addEventListener('keypress', async (e) => {
    if(e.key === 'Enter') {
        const barcode = e.target.value.trim();
        e.target.value = '';
        if(!barcode) return;
        
        // Mock rápido para el MVP si el backend aún no responde con el producto
        // En producción esto haría un fetch POST a /inventory/scan
        try {
            const res = await fetch(`${API_URL}/inventory/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ barcode: barcode })
            });
            if(res.ok) {
                const p = await res.json();
                cart.push({ id: p.id, name: p.name, price: p.price, qty: 1 });
            } else {
                // Producto no encontrado, agregamos uno genérico para la demo
                cart.push({ id: Math.random(), name: `Producto [${barcode}]`, price: 5.00, qty: 1 });
                showToast("Producto no registrado. Añadido como genérico.", true);
            }
        } catch(err) {
            cart.push({ id: Math.random(), name: `Escaneado [${barcode}]`, price: 10.00, qty: 1 });
        }
        
        updateCartUI();
    }
});

function removeFromCart(index) {
    cart.splice(index, 1);
    updateCartUI();
}

function clearCart() {
    cart = [];
    updateCartUI();
}

// Lógica del Checkout
function openCheckoutModal() {
    if(cart.length === 0) {
        showToast("El carrito está vacío", true);
        return;
    }
    const modal = document.getElementById('checkoutModal');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        document.getElementById('checkoutModalContent').classList.remove('scale-95');
    }, 10);
}

function closeCheckoutModal() {
    const modal = document.getElementById('checkoutModal');
    modal.classList.add('opacity-0');
    document.getElementById('checkoutModalContent').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

async function processPayment(method) {
    // Si es Híbrido, puedes pedir montos, aquí simplificamos el MVP
    showToast(`Procesando pago con ${method}...`);
    
    // Aquí haríamos el POST a /api/v1/pos/sale (simulado para UI)
    setTimeout(() => {
        showToast(`✅ Venta procesada exitosamente (${method})`);
        closeCheckoutModal();
        clearCart();
        loadDashboardData(); // Refrescar métricas del admin
    }, 800);
}

// 8. INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
});
