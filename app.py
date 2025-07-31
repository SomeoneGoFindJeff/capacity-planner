import os
from logging.config import dictConfig
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

# ─── Structured Logging Setup ────────────────────────────────────────────
dictConfig({
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "wsgi": {
            "class":    "logging.StreamHandler",
            "stream":   "ext://sys.stdout",
            "formatter":"default"
        },
        "file": {
            "class":     "logging.FileHandler",
            "filename":  "capacity_planner.log",
            "formatter": "default",
            "level":     "INFO"
        }
    },
    "root": {
        "level":    "INFO",
        "handlers": ["wsgi", "file"]
    }
})

# ─── Flask & SQLAlchemy Setup ────────────────────────────────────────────
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = os.getenv('DATABASE_URL', 'sqlite:///data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.logger.info("🚀 Starting Capacity Planner application")

# ─── Global Exception Handler ────────────────────────────────────────────
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception("❌ Unhandled Exception:")
    return render_template('error.html', error=e), 500

# ─────────── Models ───────────────────────────────────────────────────────
class Sprint(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(80), nullable=False)
    projects = db.relationship('Project', backref='sprint', cascade='all, delete-orphan')

class Project(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), nullable=False)
    sprint_id   = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    assignments = db.relationship('Assignment', backref='project', cascade='all, delete-orphan')

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
    sprint_id   = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    project_id  = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    capacity    = db.Column(db.Integer, default=100)

# ─── Sprint CRUD ─────────────────────────────────────────────────────────
@app.route('/')
def home():
    return redirect(url_for('list_sprints'))

@app.route('/sprints', methods=['GET'])
def list_sprints():
    sprints = Sprint.query.order_by(Sprint.id).all()
    return render_template('sprints.html', sprints=sprints)

@app.route('/sprints', methods=['POST'])
def add_sprint():
    name = request.form.get('name')
    if not name:
        app.logger.warning("Attempted to add sprint without a name")
        return redirect(url_for('list_sprints'))
    sprint = Sprint(name=name)
    db.session.add(sprint)
    db.session.commit()
    app.logger.info(f"Added Sprint(id={sprint.id}, name='{sprint.name}')")
    return redirect(url_for('list_sprints'))

@app.route('/sprints/delete/<int:sprint_id>', methods=['POST'])
def delete_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    db.session.delete(sprint)
    db.session.commit()
    app.logger.info(f"Deleted Sprint(id={sprint_id})")
    return redirect(url_for('list_sprints'))

# ─── Copy Sprint ──────────────────────────────────────────────────────────
@app.route('/sprints/copy/<int:source_id>', methods=['POST'])
def copy_sprint(source_id):
    source     = Sprint.query.get_or_404(source_id)
    new_sprint = Sprint(name=f"{source.name} Copy")
    db.session.add(new_sprint)
    db.session.flush()
    proj_map = {}
    for proj in source.projects:
        np = Project(name=proj.name, sprint_id=new_sprint.id)
        db.session.add(np)
        db.session.flush()
        proj_map[proj.id] = np.id
    for a in source.assignments:
        na = Assignment(
            sprint_id   = new_sprint.id,
            project_id  = proj_map[a.project_id],
            resource_id = a.resource_id,
            capacity    = a.capacity
        )
        db.session.add(na)
    db.session.commit()
    app.logger.info(f"Copied Sprint(id={source_id}) -> Sprint(id={new_sprint.id})")
    return redirect(url_for('view_sprint', sprint_id=new_sprint.id))

# ─── Sprint Detail ───────────────────────────────────────────────────────
@app.route('/sprints/<int:sprint_id>')
def view_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)

    # Compute each resource’s remaining capacity
    avail_resources = []
    for r in Resource.query.order_by(Resource.name).all():
        used      = sum(a.capacity for a in sprint.assignments if a.resource_id == r.id)
        remaining = 100 - used
        if remaining > 0:
            avail_resources.append((r, remaining))

    # For filter panels
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
    if not name:
        app.logger.warning("Attempted to add project without a name")
    else:
        p = Project(name=name, sprint_id=sprint_id)
        db.session.add(p)
        db.session.commit()
        app.logger.info(f"Added Project(id={p.id}, sprint_id={sprint_id})")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/delete/<int:proj_id>', methods=['POST'])
def delete_project(sprint_id, proj_id):
    proj = Project.query.get_or_404(proj_id)
    db.session.delete(proj)
    db.session.commit()
    app.logger.info(f"Deleted Project(id={proj_id}) in Sprint(id={sprint_id})")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/edit/<int:proj_id>', methods=['POST'])
def edit_project(sprint_id, proj_id):
    proj = Project.query.get_or_404(proj_id)
    new_name = request.form.get('name')
    if new_name:
        proj.name = new_name
        db.session.commit()
        app.logger.info(f"Renamed Project(id={proj_id}) to '{new_name}'")
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

# ─── Assignment APIs ─────────────────────────────────────────────────────
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
    app.logger.info(f"Assigned Resource(id={a.resource_id}) to Project(id={a.project_id}) [Sprint={a.sprint_id}]")
    return jsonify(success=True)

@app.route('/unassign', methods=['POST'])
def unassign_resource():
    data = request.json or {}
    a = Assignment.query.filter_by(
        sprint_id   = int(data.get('sprint_id', 0)),
        project_id  = int(data.get('project_id', 0)),
        resource_id = int(data.get('resource_id', 0))
    ).first()
    if a:
        db.session.delete(a)
        db.session.commit()
        app.logger.info(f"Unassigned Resource(id={a.resource_id}) from Project(id={a.project_id}) [Sprint={a.sprint_id}]")
    return jsonify(success=True)

# ─── ResourceType CRUD ──────────────────────────────────────────────────
@app.route('/types', methods=['GET'])
def list_types():
    types = ResourceType.query.order_by(ResourceType.name).all()
    return render_template('types.html', types=types)

@app.route('/types', methods=['POST'])
def add_type():
    name = request.form.get('name')
    if name:
        t = ResourceType(name=name)
        db.session.add(t)
        db.session.commit()
        app.logger.info(f"Added ResourceType(id={t.id}, name='{t.name}')")
    return redirect(url_for('list_types'))

@app.route('/types/edit/<int:type_id>', methods=['POST'])
def edit_type(type_id):
    t = ResourceType.query.get_or_404(type_id)
    name = request.form.get('name')
    if name:
        t.name = name
        db.session.commit()
        app.logger.info(f"Renamed ResourceType(id={type_id}) to '{name}'")
    return redirect(url_for('list_types'))

@app.route('/types/delete/<int:type_id>', methods=['POST'])
def delete_type(type_id):
    t = ResourceType.query.get_or_404(type_id)
    db.session.delete(t)
    db.session.commit()
    app.logger.info(f"Deleted ResourceType(id={type_id})")
    return redirect(url_for('list_types'))

# ─── ResourceGroup CRUD ─────────────────────────────────────────────────
@app.route('/groups', methods=['GET'])
def list_groups():
    groups = ResourceGroup.query.order_by(ResourceGroup.name).all()
    return render_template('groups.html', groups=groups)

@app.route('/groups', methods=['POST'])
def add_group():
    name = request.form.get('name')
    if name:
        g = ResourceGroup(name=name)
        db.session.add(g)
        db.session.commit()
        app.logger.info(f"Added ResourceGroup(id={g.id}, name='{g.name}')")
    return redirect(url_for('list_groups'))

@app.route('/groups/edit/<int:group_id>', methods=['POST'])
def edit_group(group_id):
    g = ResourceGroup.query.get_or_404(group_id)
    name = request.form.get('name')
    if name:
        g.name = name
        db.session.commit()
        app.logger.info(f"Renamed ResourceGroup(id={group_id}) to '{name}'")
    return redirect(url_for('list_groups'))

@app.route('/groups/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    g = ResourceGroup.query.get_or_404(group_id)
    db.session.delete(g)
    db.session.commit()
    app.logger.info(f"Deleted ResourceGroup(id={group_id})")
    return redirect(url_for('list_groups'))

# ─── Resource CRUD ───────────────────────────────────────────────────────
@app.route('/resources', methods=['GET'])
def list_resources():
    resources = Resource.query.order_by(Resource.name).all()
    types     = ResourceType.query.order_by(ResourceType.name).all()
    groups    = ResourceGroup.query.order_by(ResourceGroup.name).all()
    return render_template('resources.html',
                           resources=resources,
                           types=types,
                           groups=groups)

@app.route('/resources', methods=['POST'])
def add_resource():
    name     = request.form.get('name')
    type_id  = request.form.get('type_id') or None
    group_id = request.form.get('group_id') or None
    if name:
        r = Resource(
            name     = name,
            type_id  = int(type_id) if type_id else None,
            group_id = int(group_id) if group_id else None
        )
        db.session.add(r)
        db.session.commit()
        app.logger.info(f"Added Resource(id={r.id}, name='{r.name}')")
    return redirect(url_for('list_resources'))

@app.route('/resources/edit/<int:resource_id>', methods=['POST'])
def edit_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    new_name = request.form.get('name')
    type_id  = request.form.get('type_id') or None
    group_id = request.form.get('group_id') or None
    if new_name:
        r.name     = new_name
        r.type_id  = int(type_id) if type_id else None
        r.group_id = int(group_id) if group_id else None
        db.session.commit()
        app.logger.info(f"Updated Resource(id={resource_id})")
    return redirect(url_for('list_resources'))

@app.route('/resources/delete/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    db.session.delete(r)
    db.session.commit()
    app.logger.info(f"Deleted Resource(id={resource_id})")
    return redirect(url_for('list_resources'))

# ─── App Runner ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
