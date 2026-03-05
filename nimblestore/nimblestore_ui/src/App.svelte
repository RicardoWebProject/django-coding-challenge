<script>
  import { onMount } from 'svelte';
  import {
    activeTab,
    products, productsLoading, productsError, showProductForm, newProduct, editingProduct,
    orders, ordersLoading, ordersError, showOrderForm, orderItems, orderFormError, expandedOrderId,
    fetchProducts, createProduct, startEditProduct, saveProduct,
    fetchOrders, createOrder, cancelOrder, fulfillOrder,
    addOrderItem, removeOrderItem, toggleOrderDetail, formatDate,
    setNewProductField, setEditingProductField, setOrderItemField,
  } from '../scripts/baseConnection.js';

  onMount(() => {
    fetchProducts();
    fetchOrders();
  });
</script>

<!-- ── Header ──────────────────────────────────────────────────────── -->
<header>
  <span class="logo">🛒 Nimble Store</span>
  <nav>
    <button
      class="tab-btn"
      class:active={$activeTab === 'products'}
      on:click={() => $activeTab = 'products'}
    >
      Productos
    </button>
    <button
      class="tab-btn"
      class:active={$activeTab === 'orders'}
      on:click={() => $activeTab = 'orders'}
    >
      Órdenes
    </button>
  </nav>
</header>

<main>

  <!-- ── PRODUCTS TAB ───────────────────────────────────────────────── -->
  {#if $activeTab === 'products'}
    <section>
      <div class="section-header">
        <h2>Productos</h2>
        <div class="actions">
          <button on:click={fetchProducts}>↻ Refrescar</button>
          <button class="btn-primary" on:click={() => $showProductForm = !$showProductForm}>
            {$showProductForm ? '✕ Cancelar' : '+ Nuevo producto'}
          </button>
        </div>
      </div>

      {#if $productsError}
        <p class="error">{$productsError}</p>
      {/if}

      <!-- New product form -->
      {#if $showProductForm}
        <div class="card form-card">
          <h3>Nuevo producto</h3>
          <div class="form-grid">
            <label>
              Nombre
              <input type="text" value={$newProduct.name} on:input={e => setNewProductField('name', e.target.value)} placeholder="Nombre del producto" />
            </label>
            <label>
              Precio
              <input type="number" min="0" step="0.01" value={$newProduct.price} on:input={e => setNewProductField('price', e.target.value)} placeholder="0.00" />
            </label>
            <label>
              Stock
              <input type="number" min="0" value={$newProduct.stock_quantity} on:input={e => setNewProductField('stock_quantity', e.target.value)} placeholder="0" />
            </label>
          </div>
          <button class="btn-primary" on:click={createProduct}>Guardar producto</button>
        </div>
      {/if}

      <!-- Edit product form -->
      {#if $editingProduct}
        <div class="card form-card">
          <h3>Editar producto #{$editingProduct.id}</h3>
          <div class="form-grid">
            <label>
              Nombre
              <input type="text" value={$editingProduct.name} on:input={e => setEditingProductField('name', e.target.value)} />
            </label>
            <label>
              Precio
              <input type="number" min="0" step="0.01" value={$editingProduct.price} on:input={e => setEditingProductField('price', e.target.value)} />
            </label>
            <label>
              Stock
              <input type="number" min="0" value={$editingProduct.stock_quantity} on:input={e => setEditingProductField('stock_quantity', e.target.value)} />
            </label>
          </div>
          <div class="btn-row">
            <button class="btn-primary" on:click={saveProduct}>Guardar cambios</button>
            <button on:click={() => $editingProduct = null}>Cancelar</button>
          </div>
        </div>
      {/if}

      {#if $productsLoading}
        <p class="muted">Cargando productos…</p>
      {:else if $products.length === 0}
        <p class="muted">No hay productos registrados.</p>
      {:else}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {#each $products as p (p.id)}
                <tr>
                  <td class="muted">#{p.id}</td>
                  <td>{p.name}</td>
                  <td>Q{parseFloat(p.price).toFixed(2)}</td>
                  <td>
                    <span class="stock" class:low={p.stock_quantity <= 5}>
                      {p.stock_quantity}
                    </span>
                  </td>
                  <td>
                    <button class="btn-sm" on:click={() => startEditProduct(p)}>Editar</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}

  <!-- ── ORDERS TAB ─────────────────────────────────────────────────── -->
  {#if $activeTab === 'orders'}
    <section>
      <div class="section-header">
        <h2>Órdenes</h2>
        <div class="actions">
          <button on:click={fetchOrders}>↻ Refrescar</button>
          <button class="btn-primary" on:click={() => { $showOrderForm = !$showOrderForm; $orderFormError = ''; }}>
            {$showOrderForm ? '✕ Cancelar' : '+ Nueva orden'}
          </button>
        </div>
      </div>

      {#if $ordersError}
        <p class="error">{$ordersError}</p>
      {/if}

      <!-- New order form -->
      {#if $showOrderForm}
        <div class="card form-card">
          <h3>Nueva orden</h3>
          {#each $orderItems as item, i (i)}
            <div class="order-item-row">
              <label class="flex-label">
                Producto
                <select value={item.product_id} on:change={e => setOrderItemField(i, 'product_id', e.target.value)}>
                  <option value="">— seleccionar —</option>
                  {#each $products as p (p.id)}
                    <option value={p.id}>{p.name} (stock: {p.stock_quantity})</option>
                  {/each}
                </select>
              </label>
              <label class="qty-label">
                Cantidad
                <input type="number" min="1" value={item.quantity} on:input={e => setOrderItemField(i, 'quantity', e.target.value)} />
              </label>
              {#if $orderItems.length > 1}
                <button class="btn-danger btn-sm remove-btn" on:click={() => removeOrderItem(i)}>✕</button>
              {/if}
            </div>
          {/each}
          <div class="btn-row">
            <button on:click={addOrderItem}>+ Agregar producto</button>
            <button class="btn-primary" on:click={createOrder}>Confirmar orden</button>
          </div>
          {#if $orderFormError}
            <p class="error">{$orderFormError}</p>
          {/if}
        </div>
      {/if}

      {#if $ordersLoading}
        <p class="muted">Cargando órdenes…</p>
      {:else if $orders.length === 0}
        <p class="muted">No hay órdenes registradas.</p>
      {:else}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Estado</th>
                <th>Fecha</th>
                <th>Productos</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {#each $orders as o (o.id)}
                <tr>
                  <td class="muted">#{o.id}</td>
                  <td>
                    <span class="badge badge-{o.status}">{o.status}</span>
                  </td>
                  <td class="muted small">{formatDate(o.created_at)}</td>
                  <td>{o.items.length} ítem(s)</td>
                  <td class="btn-row-inline">
                    <button class="btn-sm" on:click={() => toggleOrderDetail(o.id)}>
                      {$expandedOrderId === o.id ? 'Ocultar' : 'Ver detalle'}
                    </button>
                    {#if o.status === 'pending'}
                      <button class="btn-sm btn-success" on:click={() => fulfillOrder(o.id)}>Confirmar</button>
                      <button class="btn-sm btn-danger" on:click={() => cancelOrder(o.id)}>Cancelar</button>
                    {/if}
                  </td>
                </tr>
                {#if $expandedOrderId === o.id}
                  <tr class="detail-row">
                    <td colspan="5">
                      <table class="inner-table">
                        <thead>
                          <tr>
                            <th>Producto</th>
                            <th>Cantidad</th>
                            <th>Precio unitario</th>
                            <th>Subtotal</th>
                          </tr>
                        </thead>
                        <tbody>
                          {#each o.items as item (item.id)}
                            <tr>
                              <td>{item.product_name}</td>
                              <td>{item.quantity}</td>
                              <td>Q{parseFloat(item.unit_price).toFixed(2)}</td>
                              <td>Q{(item.quantity * parseFloat(item.unit_price)).toFixed(2)}</td>
                            </tr>
                          {/each}
                          <tr class="total-row">
                            <td colspan="3"><strong>Total</strong></td>
                            <td>
                              <strong>
                                Q{o.items.reduce((acc, i) => acc + i.quantity * parseFloat(i.unit_price), 0).toFixed(2)}
                              </strong>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}

</main>