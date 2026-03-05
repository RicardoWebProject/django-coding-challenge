# Nimble Store – Coding Challenge

## The Goal

You are building the backend and frontend for a simple e-commerce store. The goal is to produce a working, well-structured application that a small team could ship and maintain. We are not looking for a perfect solution — we are looking for clean code, sensible trade-offs, and your ability to explain your decisions.

This challenge is intentionally open-ended. There are things we have deliberately left unspecified. Make reasonable choices, document them, and be prepared to defend them.

---

## Requirements

### Backend (Django + Django REST Framework)

Build a REST API for a store with **products** and **orders**.

**Products**
- Products have a name, price, and quantity in stock.
- The API should support listing, creating, and editing products.

**Orders**
- A customer places an order by selecting products and quantities.
- Placing an order must **lock in the price at the time of purchase** — a price change on the product should not retroactively affect existing orders.
- Placing an order must **deduct stock**. If a product is out of stock or the requested quantity exceeds available stock, the order must be rejected with a meaningful error.
- **Two simultaneous orders must not be able to oversell a product.** If two customers try to buy the last item at the same time, only one should succeed.
- Orders have a status. A `pending` order can be cancelled; cancelling restores the inventory. An order that has already been `fulfilled` cannot be cancelled.
- The API should support retrieving a list of orders and the details of a single order.

### Frontend (Svelte)

Build a UI on top of the API you create. The `nimblestore_ui` directory contains a Svelte app configured and ready to run — you build what goes inside it.

**User stories:**
- A user can browse available products, see name, price, and current stock.
- A user can add products to a cart and adjust quantities before submitting.
- Submitting an order shows the confirmed total, or a clear error if it failed (e.g. item went out of stock between adding to cart and submitting).
- A user can view a list of past orders.

How you structure components, manage state, and handle loading and error states is up to you.

---

## What We Will Discuss

Add a **"Decisions & Trade-offs"** section to this README when you submit. For at least **three choices** you made — across the API design, data model, or frontend — write a short paragraph on: what you chose, what the alternative was, and why you went the direction you did.

There are no wrong answers. We want to understand how you think, not just what you built.

---

## Setup

The project runs via Docker Compose. You do not need to install Python, Node, or PostgreSQL locally.

```bash
# Start all services
docker compose up --build

# In a separate terminal, apply migrations
docker compose exec django python manage.py migrate
```

- Django API: `http://localhost:8000`
- Svelte UI: `http://localhost:8080`

When you add models, create and apply migrations:
```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
```

---

## Tests

Write tests using `pytest`. Run them inside the Django container:

```bash
docker compose exec django pytest
```

Tests live in `checkout/tests/`. Cover the core behaviours — happy paths and the error cases that matter most.

---

## Code Quality

Pre-commit hooks are configured for linting and formatting. Install them once:

```bash
pip install pre-commit
pre-commit install
```

---

## Evaluation Criteria

We evaluate submissions on five dimensions:

| Dimension | What we look at |
|---|---|
| **Correctness** | Does it work? Do the core behaviours (stock deduction, price lock, cancellation) actually hold up? |
| **Architecture** | Is responsibility clearly assigned? Is business logic where it belongs? Would a new developer understand the structure quickly? |
| **Frontend quality** | Are components sensibly decomposed? Is async/error state handled gracefully? Does the UI give useful feedback? |
| **Tests** | Do the tests test *behaviour*, not just HTTP status codes? Are the important edge cases covered? |
| **Trade-off thinking** | Is the Decisions & Trade-offs section specific to *your* implementation? Can you explain why, not just what? |

Good luck.

## Decisions & Trade-offs

### 1. Entorno local con virtualenv en lugar de Docker

Se optó por levantar el proyecto directamente sobre un virtualenv local (Python 3.10) en lugar de utilizar Docker Compose desde el inicio. Si bien el proyecto ya incluye un `docker-compose.yml` funcional, configurarlo correctamente —variables de entorno, volúmenes, red interna, build de la imagen de Node— habría añadido fricción al inicio del desarrollo y dificultado la iteración rápida. La alternativa de Docker sigue siendo válida y está lista para producción o para un equipo que trabaje en distintos sistemas operativos; simplemente se priorizó tener la estructura base funcional primero, con el entendimiento de que la contenedorización es un paso posterior de despliegue, no un prerequisito de desarrollo.

### 2. Lógica de negocio en los serializadores, no en las vistas

Toda la lógica de validación y escritura de órdenes —verificación de stock, bloqueo de precio, deducción de inventario— vive en `OrderCreateSerializer.create()`, no en la vista. Las vistas (`views.py`) se limitan a orquestar el ciclo request-response: deserializar la entrada, delegar al serializador y devolver la respuesta apropiada. La alternativa habría sido concentrar esa lógica directamente en el método `create()` o `perform_create()` de la vista, lo cual es un patrón habitual en proyectos pequeños de DRF. Se eligió el serializador porque encapsula mejor la lógica reutilizable (el mismo serializador podría invocarse desde una tarea asíncrona o un comando de gestión), y porque mantiene las vistas delgadas y fáciles de leer.

### 3. Agregar lo necesario, sin sobre-diseñar

Se identificó que el flujo de negocio requería inevitablemente un punto de transición de `pending` a `fulfilled`, aunque el enunciado no lo mencionara explícitamente: sin él, una orden nunca avanza y la cancelación pierde sentido. Por eso se añadió el endpoint `POST /api/orders/<pk>/fulfill/`. Sin embargo, se decidió no implementar autenticación ni gestión de usuarios: habría implicado introducir modelos de sesión, tokens JWT o sesiones de Django, permisos por objeto, y pruebas adicionales, por un beneficio que no era central al desafío planteado. Es una funcionalidad que se consideraría en un release posterior, una vez validado el flujo principal.

### 4. Separación de responsabilidades en el frontend

Aunque la aplicación es modesta en tamaño y podría haberse escrito en un único archivo `.svelte`, se optó desde el principio por separar en tres capas: `scripts/baseConnection.js` concentra todo el estado (Svelte writable stores) y las llamadas a la API; `src/App.svelte` actúa como capa de presentación pura, consumiendo stores y funciones sin contener lógica propia; y `public/global.css` centraliza los estilos. Esta estructura facilita que cualquier desarrollador que se incorpore al proyecto localice rápidamente dónde vive cada responsabilidad, y hace que las funciones de la API sean independientes del framework de UI —podrían extraerse a un módulo TypeScript sin modificar la plantilla.

### 5. Bloqueo pesimista con orden determinista para prevenir condiciones de carrera

El requisito de que dos órdenes simultáneas no puedan sobrepasar el stock disponible se resolvió mediante `SELECT FOR UPDATE` dentro de una transacción atómica en el serializador. El detalle clave es que los productos se bloquean **siempre en orden ascendente por `pk`**, independientemente del orden en que lleguen en el payload. Esto elimina la posibilidad de un deadlock circular: si dos transacciones concurrentes intentan bloquear los productos A y B, ambas los adquirirán en el mismo orden y una simplemente esperará a que la otra libere el lock, en lugar de bloquearse mutuamente. La alternativa habría sido un bloqueo optimista con reintentos (usando un campo `version` o chequeando el stock antes y después sin lock), pero esa estrategia traslada la gestión de reintentos al cliente y complica el manejo de errores. El bloqueo pesimista es más simple de razonar y correcto por construcción.

