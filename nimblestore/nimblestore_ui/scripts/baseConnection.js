import { writable, get } from 'svelte/store';

const API = 'http://localhost:8000';

// ── Tab ───────────────────────────────────────────────────────────────
export const activeTab = writable('products');

// ── Products state ────────────────────────────────────────────────────
export const products       = writable([]);
export const productsLoading = writable(false);
export const productsError  = writable('');
export const showProductForm = writable(false);
export const newProduct      = writable({ name: '', price: '', stock_quantity: '' });
export const editingProduct  = writable(null);

// ── Orders state ──────────────────────────────────────────────────────
export const orders          = writable([]);
export const ordersLoading   = writable(false);
export const ordersError     = writable('');
export const expandedOrderId = writable(null);

// ── Cart state ────────────────────────────────────────────────────────
export const cart             = writable([]);
export const cartError        = writable('');
export const lastCreatedOrder = writable(null);

// ── Nested-field helpers (stores don't support bind on properties) ────
export function setNewProductField(field, value) {
  newProduct.update(p => ({ ...p, [field]: value }));
}

export function setEditingProductField(field, value) {
  editingProduct.update(p => ({ ...p, [field]: value }));
}

// ── Products API ──────────────────────────────────────────────────────
export async function fetchProducts() {
  productsLoading.set(true);
  productsError.set('');
  try {
    const res = await fetch(`${API}/api/products/`);
    if (!res.ok) throw new Error('Error al cargar productos.');
    products.set(await res.json());
  } catch (e) {
    productsError.set(e.message);
  } finally {
    productsLoading.set(false);
  }
}

export async function createProduct() {
  productsError.set('');
  const p = get(newProduct);
  try {
    const res = await fetch(`${API}/api/products/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: p.name,
        price: parseFloat(p.price),
        stock_quantity: parseInt(p.stock_quantity),
      }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(JSON.stringify(data));
    }
    newProduct.set({ name: '', price: '', stock_quantity: '' });
    showProductForm.set(false);
    await fetchProducts();
  } catch (e) {
    productsError.set(e.message);
  }
}

export function startEditProduct(p) {
  editingProduct.set({ ...p });
}

export async function saveProduct() {
  productsError.set('');
  const ep = get(editingProduct);
  try {
    const res = await fetch(`${API}/api/products/${ep.id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: ep.name,
        price: parseFloat(ep.price),
        stock_quantity: parseInt(ep.stock_quantity),
      }),
    });
    if (!res.ok) throw new Error('Error al guardar el producto.');
    editingProduct.set(null);
    await fetchProducts();
  } catch (e) {
    productsError.set(e.message);
  }
}

// ── Orders API ────────────────────────────────────────────────────────
export async function fetchOrders() {
  ordersLoading.set(true);
  ordersError.set('');
  try {
    const res = await fetch(`${API}/api/orders/`);
    if (!res.ok) throw new Error('Error al cargar órdenes.');
    orders.set(await res.json());
  } catch (e) {
    ordersError.set(e.message);
  } finally {
    ordersLoading.set(false);
  }
}

export function addToCart(product) {
  cart.update(items => {
    const idx = items.findIndex(i => i.product.id === product.id);
    if (idx >= 0) {
      const copy = [...items];
      copy[idx] = { ...copy[idx], quantity: copy[idx].quantity + 1 };
      return copy;
    }
    return [...items, { product, quantity: 1 }];
  });
}

export function removeFromCart(productId) {
  cart.update(items => items.filter(i => i.product.id !== productId));
}

export function setCartItemQuantity(productId, qty) {
  const n = parseInt(qty);
  if (isNaN(n) || n < 1) return;
  cart.update(items =>
    items.map(i => i.product.id === productId ? { ...i, quantity: n } : i)
  );
}

export function clearCart() {
  cart.set([]);
  cartError.set('');
}

export async function submitCart() {
  cartError.set('');
  const items = get(cart);
  if (!items.length) {
    cartError.set('El carrito está vacío.');
    return;
  }
  try {
    const res = await fetch(`${API}/api/orders/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map(i => ({
          product: i.product.id,
          quantity: i.quantity,
        })),
      }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(JSON.stringify(data));
    }
    const order = await res.json();
    lastCreatedOrder.set(order);
    cart.set([]);
    await fetchOrders();
  } catch (e) {
    cartError.set(e.message);
  }
}

export async function cancelOrder(id) {
  ordersError.set('');
  try {
    const res = await fetch(`${API}/api/orders/${id}/cancel/`, { method: 'POST' });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Error al cancelar la orden.');
    }
    await fetchOrders();
  } catch (e) {
    ordersError.set(e.message);
  }
}

export async function fulfillOrder(id) {
  ordersError.set('');
  try {
    const res = await fetch(`${API}/api/orders/${id}/fulfill/`, { method: 'POST' });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Error al confirmar la orden.');
    }
    await fetchOrders();
  } catch (e) {
    ordersError.set(e.message);
  }
}

export function toggleOrderDetail(id) {
  expandedOrderId.update(current => current === id ? null : id);
}

export function formatDate(dt) {
  return new Date(dt).toLocaleString('es-MX', {
    dateStyle: 'medium', timeStyle: 'short',
  });
}
