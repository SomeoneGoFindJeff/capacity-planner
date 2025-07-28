from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─────────── Models ───────────
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
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    resources = db.relationship('Resource', backref='type', cascade='all, delete-orphan')

class ResourceGroup(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
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
    sprint      = db.relationship('Sprint', backref='assignments')

# ─── Sprint CRUD ───
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
    if name:
        db.session.add(Sprint(name=name))
        db.session.commit()
    return redirect(url_for('list_sprints'))

@app.route('/sprints/delete/<int:sprint_id>', methods=['POST'])
def delete_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    db.session.delete(sprint)
    db.session.commit()
    return redirect(url_for('list_sprints'))

# ─── Copy Sprint ───
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
    return redirect(url_for('view_sprint', sprint_id=new_sprint.id))

# ─── Sprint Detail ───
@app.route('/sprints/<int:sprint_id>')
def view_sprint(sprint_id):
    sprint       = Sprint.query.get_or_404(sprint_id)
    assigned_ids = [a.resource_id for a in sprint.assignments]
    available    = Resource.query.filter(Resource.id.notin_(assigned_ids)) \
                                  .order_by(Resource.name).all()
    # Pass filter data as before...
    return render_template('sprint_detail.html',
                           sprint=sprint,
                           available_resources=available,
                           filter_types=ResourceType.query.order_by(ResourceType.name).all(),
                           filter_groups=ResourceGroup.query.order_by(ResourceGroup.name).all())

# ─── Project CRUD ───
@app.route('/sprints/<int:sprint_id>/projects', methods=['POST'])
def add_project(sprint_id):
    name = request.form.get('name')
    if name:
        db.session.add(Project(name=name, sprint_id=sprint_id))
        db.session.commit()
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/delete/<int:proj_id>', methods=['POST'])
def delete_project(sprint_id, proj_id):
    proj = Project.query.get_or_404(proj_id)
    db.session.delete(proj)
    db.session.commit()
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

@app.route('/sprints/<int:sprint_id>/projects/edit/<int:proj_id>', methods=['POST'])
def edit_project(sprint_id, proj_id):
    proj = Project.query.get_or_404(proj_id)
    new_name = request.form.get('name')
    if new_name:
        proj.name = new_name
        db.session.commit()
    return redirect(url_for('view_sprint', sprint_id=sprint_id))

# ─── Assignment APIs ───
@app.route('/assign', methods=['POST'])
def assign_resource():
    data        = request.json
    db.session.add(Assignment(
        sprint_id   = int(data['sprint_id']),
        project_id  = int(data['project_id']),
        resource_id = int(data['resource_id']),
        capacity    = int(data.get('capacity', 100))
    ))
    db.session.commit()
    return jsonify(success=True)

@app.route('/unassign', methods=['POST'])
def unassign_resource():
    data        = request.json
    a = Assignment.query.filter_by(
        sprint_id   = int(data['sprint_id']),
        project_id  = int(data['project_id']),
        resource_id = int(data['resource_id'])
    ).first()
    if a:
        db.session.delete(a)
        db.session.commit()
    return jsonify(success=True)

# ─── ResourceType CRUD ───
@app.route('/types')
def list_types():
    types = ResourceType.query.order_by(ResourceType.name).all()
    return render_template('types.html', types=types)

@app.route('/types', methods=['POST'])
def add_type():
    name = request.form.get('name')
    if name:
        db.session.add(ResourceType(name=name))
        db.session.commit()
    return redirect(url_for('list_types'))

@app.route('/types/edit/<int:type_id>', methods=['POST'])
def edit_type(type_id):
    t = ResourceType.query.get_or_404(type_id)
    name = request.form.get('name')
    if name:
        t.name = name
        db.session.commit()
    return redirect(url_for('list_types'))

@app.route('/types/delete/<int:type_id>', methods=['POST'])
def delete_type(type_id):
    t = ResourceType.query.get_or_404(type_id)
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for('list_types'))

# ─── ResourceGroup CRUD ───
@app.route('/groups')
def list_groups():
    groups = ResourceGroup.query.order_by(ResourceGroup.name).all()
    return render_template('groups.html', groups=groups)

@app.route('/groups', methods=['POST'])
def add_group():
    name = request.form.get('name')
    if name:
        db.session.add(ResourceGroup(name=name))
        db.session.commit()
    return redirect(url_for('list_groups'))

@app.route('/groups/edit/<int:group_id>', methods=['POST'])
def edit_group(group_id):
    g = ResourceGroup.query.get_or_404(group_id)
    name = request.form.get('name')
    if name:
        g.name = name
        db.session.commit()
    return redirect(url_for('list_groups'))

@app.route('/groups/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    g = ResourceGroup.query.get_or_404(group_id)
    db.session.delete(g)
    db.session.commit()
    return redirect(url_for('list_groups'))

# ─── Resource CRUD ───
@app.route('/resources')
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
        r = Resource(name=name,
                     type_id=int(type_id) if type_id else None,
                     group_id=int(group_id) if group_id else None)
        db.session.add(r)
        db.session.commit()
    return redirect(url_for('list_resources'))

@app.route('/resources/edit/<int:resource_id>', methods=['POST'])
def edit_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    r.name     = request.form.get('name')
    tid        = request.form.get('type_id') or None
    gid        = request.form.get('group_id') or None
    r.type_id  = int(tid) if tid else None
    r.group_id = int(gid) if gid else None
    db.session.commit()
    return redirect(url_for('list_resources'))

@app.route('/resources/delete/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for('list_resources'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
