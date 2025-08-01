import os
from logging.config import dictConfig
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, flash
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# ─── Logging Setup ──────────────────────────────────────────────────────
dictConfig({
    "version": 1,
    "formatters": {"default": {"format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"}},
    "handlers": {
        "wsgi": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "default"},
        "file": {"class": "logging.FileHandler", "filename": "capacity_planner.log", "formatter": "default", "level": "INFO"}
    },
    "root": {"level": "INFO", "handlers": ["wsgi", "file"]}
})

# ─── App & DB Setup ────────────────────────────────────────────────────
app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev")
os.makedirs(app.instance_path, exist_ok=True)
app.config.from_pyfile('settings.py', silent=True)

# default to SQLite in instance/data.db, or use DATABASE_URL
default_sqlite = f"sqlite:///{os.path.join(app.instance_path, 'data.db')}"
db_url = os.environ.get("DATABASE_URL", default_sqlite)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── DIAGNOSTICS: ensure we’re using Postgres, not falling back to SQLite ─
app.logger.info(f"🔍 Using DATABASE_URL={db_url}")
if db_url == default_sqlite:
    raise RuntimeError("❗️DATABASE_URL not set! Persistence disabled.")

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ─── Global Error Handler ───────────────────────────────────────────────
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception("❌ Unhandled Exception:")
    return render_template('error.html', error=e), 500

# ─── Models ─────────────────────────────────────────────────────────────
class Sprint(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), nullable=False)
    projects    = db.relationship('Project',    backref='sprint',    cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='sprint',    cascade='all, delete-orphan')

class Project(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), nullable=False)
    sprint_id   = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    assignments = db.relationship('Assignment', backref='project',   cascade='all, delete-orphan')

class ResourceType(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(80), unique=True, nullable=False)
    resources = db.relationship('Resource', backref='type', cascade='all, delete-orphan')

class ResourceGroup(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(80), unique=True, nullable=False)
    resources = db.relationship('Resource', backref='group', cascade='all, delete-orphan')

class Resource(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), unique=True, nullable=False)
    type_id     = db.Column(db.Integer, db.ForeignKey('resource_type.id'), nullable=True)
    group_id    = db.Column(db.Integer, db.ForeignKey('resource_group.id'), nullable=True)
    assignments = db.relationship('Assignment', backref='resource', cascade='all, delete-orphan')

class Assignment(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sprint_id   = db.Column(db.Integer, db.ForeignKey('sprint.id'),    nullable=False)
    project_id  = db.Column(db.Integer, db.ForeignKey('project.id'),   nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'),  nullable=False)
    capacity    = db.Column(db.Integer, default=100)

# ─── Sprint Views ────────────────────────────────────────────────────────
@app.route('/')
def home():
    return redirect(url_for('list_sprints'))

@app.route('/sprints')
def list_sprints():
    sprints = Sprint.query.order_by(Sprint.id).all()
    return render_template('sprints.html', sprints=sprints)

@app.route('/sprints', methods=['POST'])
def add_sprint():
    name = request.form.get('name')
    if not name:
        flash("Please enter a sprint name.", "warning")
        return redirect(url_for('list_sprints'))
    s = Sprint(name=name)
    db.session.add(s)
    db.session.commit()
    app.logger.info(f"Added Sprint(id={s.id})")
    return redirect(url_for('list_sprints'))

@app.route('/sprints/delete/<int:sprint_id>', methods=['POST'])
def delete_sprint(sprint_id):
    s = Sprint.query.get_or_404(sprint_id)
    db.session.delete(s)
    db.session.commit()
    app.logger.info(f"Deleted Sprint(id={sprint_id})")
    return redirect(url_for('list_sprints'))

@app.route('/sprints/<int:sprint_id>')
def view_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    avail_resources = []
    for r in Resource.query.order_by(Resource.name).all():
        used      = sum(a.capacity for a in sprint.assignments if a.resource_id == r.id)
        remaining = 100 - used
        if remaining > 0:
            avail_resources.append((r, remaining))
    types  = ResourceType.query.order_by(ResourceType.name).all()
    groups = ResourceGroup.query.order_by(ResourceGroup.name).all()
    return render_template(
        'sprint_detail.html',
        sprint=sprint,
        avail_resources=avail_resources,
        filter_types=types,
        filter_groups=groups
    )

# ─── Project CRUD ────────────────────────────────────────────────────────
@app.route('/sprints/<int:sprint_id>/projects', methods=['POST'])
def add_project(sprint_id):
    name = request.form.get('name')
    if name:
        p = Project(name=name, sprint_id=sprint_id)
        db.session.add(p)
        db.session.commit()
        app.logger.info(f"Added Project(id={p.id}) to Sprint(id={sprint_id})")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/edit/<int:proj_id>', methods=['POST'])
def edit_project(sprint_id, proj_id):
    new_name = request.form.get('name')
    proj     = Project.query.get_or_404(proj_id)
    if new_name:
        proj.name = new_name
        db.session.commit()
        app.logger.info(f"Renamed Project(id={proj_id})")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/delete/<int:proj_id>', methods=['POST'])
def delete_project(sprint_id, proj_id):
    proj = Project.query.get_or_404(proj_id)
    db.session.delete(proj)
    db.session.commit()
    app.logger.info(f"Deleted Project(id={proj_id})")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

# ─── Assign / Unassign APIs ──────────────────────────────────────────────
@app.route('/assign', methods=['POST'])
def assign_resource():
    data = request.json or {}
    a = Assignment(
        sprint_id   = int(data.get('sprint_id', 0)),
        project_id  = int(data.get('project_id', 0)),
        resource_id = int(data.get('resource_id', 0)),
        capacity    = int(data.get('capacity', 100))
    )
    db.session.add(a)
    db.session.commit()
    app.logger.info(f"Assigned Resource(id={a.resource_id})")
    return jsonify(success=True)

@app.route('/unassign', methods=['POST'])
def unassign_resource():
    data = request.json or {}
    sid = data.get('sprint_id')
    pid = data.get('project_id')
    rid = data.get('resource_id')
    a = Assignment.query.filter_by(
        sprint_id=sid, project_id=pid, resource_id=rid
    ).first()
    if a:
        db.session.delete(a)
        db.session.commit()
        app.logger.info(f"Unassigned Resource(id={rid})")
        return jsonify(success=True)
    return jsonify(success=False), 404

# ─── Resource Type CRUD ─────────────────────────────────────────────────
@app.route('/types')
def list_types():
    ts = ResourceType.query.order_by(ResourceType.name).all()
    return render_template('types.html', types=ts)

@app.route('/types', methods=['POST'])
def add_type():
    name = request.form.get('name')
    if not name:
        flash("Please enter a type name.", "warning")
        return redirect(url_for('list_types'))
    t = ResourceType(name=name)
    db.session.add(t)
    try:
        db.session.commit()
        app.logger.info(f"Added ResourceType(id={t.id})")
    except IntegrityError:
        db.session.rollback()
        flash(f"Type '{name}' already exists.", "warning")
    return redirect(url_for('list_types'))

@app.route('/types/edit/<int:type_id>', methods=['POST'])
def edit_type(type_id):
    new_name = request.form.get('name')
    t = ResourceType.query.get_or_404(type_id)
    if new_name:
        t.name = new_name
        try:
            db.session.commit()
            app.logger.info(f"Renamed ResourceType(id={type_id})")
        except IntegrityError:
            db.session.rollback()
            flash(f"Type '{new_name}' already exists.", "warning")
    return redirect(url_for('list_types'))

@app.route('/types/delete/<int:type_id>', methods=['POST'])
def delete_type(type_id):
    t = ResourceType.query.get_or_404(type_id)
    db.session.delete(t)
    db.session.commit()
    app.logger.info(f"Deleted ResourceType(id={type_id})")
    return redirect(url_for('list_types'))

# ─── Resource Group CRUD ─────────────────────────────────────────────────
@app.route('/groups')
def list_groups():
    gs = ResourceGroup.query.order_by(ResourceGroup.name).all()
    return render_template('groups.html', groups=gs)

@app.route('/groups', methods=['POST'])
def add_group():
    name = request.form.get('name')
    if not name:
        flash("Please enter a group name.", "warning")
        return redirect(url_for('list_groups'))
    g = ResourceGroup(name=name)
    db.session.add(g)
    try:
        db.session.commit()
        app.logger.info(f"Added ResourceGroup(id={g.id})")
    except IntegrityError:
        db.session.rollback()
        flash(f"Group '{name}' already exists.", "warning")
    return redirect(url_for('list_groups'))

@app.route('/groups/edit/<int:group_id>', methods=['POST'])
def edit_group(group_id):
    new_name = request.form.get('name')
    g = ResourceGroup.query.get_or_404(group_id)
    if new_name:
        g.name = new_name
        try:
            db.session.commit()
            app.logger.info(f"Renamed ResourceGroup(id={group_id})")
        except IntegrityError:
            db.session.rollback()
            flash(f"Group '{new_name}' already exists.",("warning"))
    return redirect(url_for('list_groups'))

@app.route('/groups/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    g = ResourceGroup.query.get_or_404(group_id)
    db.session.delete(g)
    db.session.commit()
    app.logger.info(f"Deleted ResourceGroup(id={group_id})")
    return redirect(url_for('list_groups'))

# ─── Ensure tables exist & run ───────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
