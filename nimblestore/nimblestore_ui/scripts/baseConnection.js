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
export const orders         = writable([]);
export const ordersLoading  = writable(false);
export const ordersError    = writable('');
export const showOrderForm  = writable(false);
export const orderItems     = writable([{ product_id: '', quantity: 1 }]);
export const orderFormError = writable('');
export const expandedOrderId = writable(null);

// ── Nested-field helpers (stores don't support bind on properties) ────
export function setNewProductField(field, value) {
  newProduct.update(p => ({ ...p, [field]: value }));
}

export function setEditingProductField(field, value) {
  editingProduct.update(p => ({ ...p, [field]: value }));
}

export function setOrderItemField(index, field, value) {
  orderItems.update(items => {
    const copy = [...items];
    copy[index] = { ...copy[index], [field]: value };
    return copy;
  });
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

export async function createOrder() {
  orderFormError.set('');
  const items = get(orderItems).filter(i => i.product_id !== '' && i.quantity > 0);
  if (!items.length) {
    orderFormError.set('Agrega al menos un producto.');
    return;
  }
  try {
    const res = await fetch(`${API}/api/orders/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map(i => ({
          product: parseInt(i.product_id),
          quantity: parseInt(i.quantity),
        })),
      }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(JSON.stringify(data));
    }
    orderItems.set([{ product_id: '', quantity: 1 }]);
    showOrderForm.set(false);
    await fetchOrders();
  } catch (e) {
    orderFormError.set(e.message);
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

export function addOrderItem() {
  orderItems.update(items => [...items, { product_id: '', quantity: 1 }]);
}

export function removeOrderItem(i) {
  orderItems.update(items => items.filter((_, idx) => idx !== i));
}

export function toggleOrderDetail(id) {
  expandedOrderId.update(current => current === id ? null : id);
}

export function formatDate(dt) {
  return new Date(dt).toLocaleString('es-MX', {
    dateStyle: 'medium', timeStyle: 'short',
  });
}
