document.addEventListener('DOMContentLoaded', () => {
  // ─── Helper to wire up each resource item ───
  function setupResource(el) {
    el.addEventListener('dragstart', ev => {
      ev.dataTransfer.setData('text/plain', el.dataset.id);
      ev.dataTransfer.setData('application/capacity', el.dataset.capacity);
    });
    el.addEventListener('contextmenu', ev => {
      ev.preventDefault();
      const baseName = ev.target.textContent.replace(/\s*\(\d+%\)$/, '');
      const input = prompt(
        `Split capacity for "${baseName.trim()}" as A/B (sum to 100):`,
        '50/50'
      );
      if (!input) return;
      const parts = input.split('/').map(n => parseInt(n.trim()));
      if (
        parts.length !== 2 ||
        parts.some(isNaN) ||
        parts[0] + parts[1] !== 100
      ) {
        alert('Enter two numbers that sum to 100, e.g. 30/70.');
        return;
      }
      const container = ev.target.parentElement;
      ev.target.remove();
      parts.forEach(cap => {
        const li = document.createElement('li');
        li.className = 'draggable-resource';
        li.draggable = true;
        li.dataset.id = el.dataset.id;
        li.dataset.capacity = cap;
        li.textContent = `${baseName.trim()} (${cap}%)`;
        container.appendChild(li);
        setupResource(li);
      });
    });
  }

  // ─── Wire up all available resources for drag/split ───
  document.querySelectorAll('.draggable-resource').forEach(el => {
    if (!el.dataset.capacity) el.dataset.capacity = '100';
    setupResource(el);
  });

  // ─── Project dropzones ───
  document.querySelectorAll('.project-dropzone').forEach(zone => {
    zone.addEventListener('dragover', ev => {
      ev.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => {
      zone.classList.remove('dragover');
    });
    zone.addEventListener('drop', async ev => {
      ev.preventDefault();
      zone.classList.remove('dragover');
      const resId    = ev.dataTransfer.getData('text/plain');
      const capacity = ev.dataTransfer.getData('application/capacity');
      const projId   = zone.dataset.projectId;
      const sprintId = zone.closest('[data-sprint-id]').dataset.sprintId;
      await fetch('/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprint_id: sprintId,
          project_id: projId,
          resource_id: resId,
          capacity: capacity
        })
      });
      window.location.reload();
    });
  });

  // ─── Unassign buttons ───
  document.querySelectorAll('.unassign-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const projZone = btn.closest('.project-dropzone');
      const sprintId = projZone.closest('[data-sprint-id]').dataset.sprintId;
      await fetch('/unassign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprint_id: sprintId,
          project_id: projZone.dataset.projectId,
          resource_id: btn.dataset.resourceId
        })
      });
      window.location.reload();
    });
  });

  // ─── FILTERING LOGIC ───
  // select only the checkbox inputs, not the container divs
  const typeCheckboxes  = Array.from(document.querySelectorAll('input.filter-type'));
  const groupCheckboxes = Array.from(document.querySelectorAll('input.filter-group'));

  function filterResources() {
    const selectedTypes  = typeCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
    const selectedGroups = groupCheckboxes.filter(cb => cb.checked).map(cb => cb.value);

    document.querySelectorAll('#resource-pool .draggable-resource').forEach(li => {
      const t = li.dataset.typeId;
      const g = li.dataset.groupId;
      const okType  = !selectedTypes.length  || (t && selectedTypes.includes(t));
      const okGroup = !selectedGroups.length || (g && selectedGroups.includes(g));
      li.style.display = (okType && okGroup) ? '' : 'none';
    });
  }

  typeCheckboxes.forEach(cb => cb.addEventListener('change', filterResources));
  groupCheckboxes.forEach(cb => cb.addEventListener('change', filterResources));

  // initial filter pass
  filterResources();
});
