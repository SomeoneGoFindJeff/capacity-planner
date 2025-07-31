# TECHSPECS: Capacity Planner

**Purpose of This Document**  
This Technical Specification (“TECHSPECS”) serves as a comprehensive reference for developers, architects, or future contributors. It captures the full scope of the Capacity Planner application—its architecture, data model, routing, client logic, deployment pipeline, and extension points—so that anyone opening a new chat or joining the project can quickly get up to speed.

---

## 1. Overview & Purpose

- **Mission**: Enable Program Managers and Scrum Masters to visualize and allocate team capacity across multiple projects and sprints.  
- **Primary Users**: PMs, Scrum Masters, Resource Managers.  
- **Key Screens**:  
  1. **Sprint List** (`/sprints`)  
     - Show all Sprints; add, delete, copy, or rename.  
  2. **Sprint Detail** (`/sprints/<id>`)  
     - Display Projects + Available Resources panel; drag/drop assignments; split capacity; filter by Type/Group.  
  3. **Resources** (`/resources`)  
     - CRUD for Resources with Metadata (Name, Type, Group).  
  4. **Types / Groups** (`/types`, `/groups`)  
     - CRUD for classification lists.

---

## 2. Tech Stack & Dependencies

- **Backend**  
  - Python 3.9+, Flask 3.1.1, Flask-SQLAlchemy 3.1.1  
  - SQLite (`instance/data.db`)  
- **Frontend**  
  - Jinja2 templates, vanilla JavaScript (Drag-and-Drop API, contextmenu event)  
  - Google Material Icons  
- **Styling**  
  - CSS flex layout, overflow scroll, badge-style metadata  
- **Hosting & CI/CD**  
  - GitHub → Render (free tier)  
  - `requirements.txt`, build: `pip install -r requirements.txt`, start: `gunicorn app:app --bind 0.0.0.0:$PORT`  
- **Dev Tools**  
  - VS Code, Python extension, local venv

---

## 3. Data Model & ER Diagram

- **Sprint**  
  - `id: Integer PK`  
  - `name: String`  
  - ⭢ One-to-many → Projects, Assignments  
- **Project**  
  - `id: Integer PK`  
  - `name: String`  
  - `sprint_id: Integer FK`  
  - ⭢ One-to-many → Assignments  
- **ResourceType**  
  - `id: Integer PK`  
  - `name: String (unique)`  
- **ResourceGroup**  
  - `id: Integer PK`  
  - `name: String (unique)`  
- **Resource**  
  - `id: Integer PK`  
  - `name: String (unique)`  
  - `type_id: Integer FK → ResourceType`  
  - `group_id: Integer FK → ResourceGroup`  
  - ⭢ One-to-many → Assignments  
- **Assignment**  
  - `id: Integer PK`  
  - `sprint_id: Integer FK`  
  - `project_id: Integer FK`  
  - `resource_id: Integer FK`  
  - `capacity: Integer (percent)`

---

## 4. Directory Layout
```

```csharp
/capacity-planner
|— app.py # Flask entrypoint & routes
|— requirements.txt # Python deps
|— instance/
| └— data.db # SQLite DB
|— templates/ # Jinja2 templates
| ├— base.html
| ├— sprints.html
| ├— sprint_detail.html
| ├— resources.html
| ├— types.html
| └— groups.html
|— static/
| ├— style.css
| └— app.js # Client logic
└— venv/ # Virtual env
```

---

## 5. Routing & API Endpoints

| Route                             | Method | Description                               |
|-----------------------------------|--------|-------------------------------------------|
| `/`                               | GET    | Redirect to `/sprints`                    |
| `/sprints`                        | GET    | List all Sprints                          |
| `/sprints`                        | POST   | Add new Sprint                            |
| `/sprints/delete/<int:id>`        | POST   | Delete Sprint                             |
| `/sprints/copy/<int:src_id>`      | POST   | Copy Sprint + Projects/Assignments        |
| `/sprints/<int:sprint_id>`        | GET    | Sprint detail (projects + available)      |
| `/sprints/<int:sprint_id>/projects` | POST | Add Project to Sprint                     |
| `/sprints/.../projects/edit/...`  | POST   | Edit/Delete Project                       |
| `/assign`                         | POST   | JSON assign resource (with capacity)      |
| `/unassign`                       | POST   | JSON unassign resource                    |
| `/resources`                      | GET    | List Resources                            |
| `/resources`                      | POST   | Add Resource                              |
| `/resources/edit/<int:id>`        | POST   | Edit Resource (name, type, group)         |
| `/resources/delete/<int:id>`      | POST   | Delete Resource                           |
| `/types`, `/groups`               | GET/POST/EDIT/DELETE for metadata lists  |

---

## 6. Database Initialization & Migrations

- On startup, `db.create_all()` ensures tables exist.  
- No migration tool; schema changes require manual reset or future Alembic integration.

---

## 7. Frontend Architecture

- **Template Inheritance**:  
  `base.html` defines global layout and `{% block content %}`.  
- **Material Icons** via Google’s font CDN.  

---

## 8. Client-side Logic (`static/app.js`)

1. **setupResource(el)**  
   - `dragstart`: sets `dataTransfer` ID + capacity  
   - `contextmenu`: prompts split, removes original `<li>`, appends two new slots  
2. **Project Dropzones**  
   - `dragover`/`dragleave` for styling  
   - `drop`: POST `/assign`, reload  
3. **Unassign Buttons**  
   - POST `/unassign`, reload  
4. **Filtering**  
   - Multi-checkbox Type & Group filters, hides/shows slots

---

## 9. Styling & Layout

- Flex containers for side-by-side panels  
- `.projects-container` horizontal scroll for overflow  
- Metadata badges styled with small `<span>`s  
- Capacity percentages beneath names

---

## 10. Deployment Pipeline

1. **GitHub** push → **Render** auto build & deploy  
2. **Build**: `pip install -r requirements.txt`  
3. **Start**: `gunicorn app:app --bind 0.0.0.0:$PORT`  
4. **Env Var**: `FLASK_ENV=development` for tracebacks  
5. **Logs**: view build/runtime in Render dashboard

---

## 11. Logging & Debugging

- **Local**: Flask’s interactive debugger shows tracebacks.  
- **Render**: Logs tab surfaces errors; use `print()` or Python `logging`.

---

## 12. Extensibility & Next Steps

- Integrate **Alembic** for DB migrations  
- Add **authentication/authorization** (Flask-Login, OAuth)  
- Implement **automated tests** (pytest, Selenium)  
- Provide **export** (CSV/XLSX) of sprint assignments  
- Build a **calendar view** of capacity over time  
- Support **real-time updates** via WebSockets

---

## 13. References

- **Flask**: https://flask.palletsprojects.com/  
- **SQLAlchemy**: https://docs.sqlalchemy.org/  
- **Render Docs**: https://render.com/docs  
- **MDN Drag-and-Drop API**: https://developer.mozilla.org/docs/Web/API/HTML_Drag_and_Drop_API  
- **Jinja2**: https://jinja.palletsprojects.com/  

