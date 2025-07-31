// static/app.js
document.addEventListener('DOMContentLoaded', () => {
  // ─── Toggle edit-panel on edit-icon click ──────────────────────────
  document.querySelectorAll('.edit-toggle').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.preventDefault();
      const id    = btn.dataset.resourceId;
      const panel = document.getElementById(`edit-panel-${id}`);
      panel.hidden = !panel.hidden;
    });
  });

  // ─── Cancel button inside panel ───────────────────────────────────
  document.querySelectorAll('.cancel-edit').forEach(btn => {
    btn.addEventListener('click', ev => {
      const id    = btn.dataset.resourceId;
      const panel = document.getElementById(`edit-panel-${id}`);
      panel.hidden = true;
    });
  });

  // ─── Helper: make a resource draggable & splittable ─────────────
  function setupResource(el) {
    el.addEventListener('dragstart', ev => {
      ev.dataTransfer.setData('text/plain', el.dataset.id);
      ev.dataTransfer.setData('application/capacity', el.dataset.capacity);
    });

    el.addEventListener('contextmenu', ev => {
      ev.preventDefault();
      const li = el;
      const originalHTML = li.innerHTML;
      const baseName = li.querySelector('strong')?.textContent || '';
      const input = prompt(
        `Split capacity for "${baseName}" as A/B (sum to 100):`,
        '50/50'
      );
      if (!input) return;
      const parts = input.split('/').map(n => parseInt(n.trim()));
      if (
        parts.length !== 2 ||
        parts.some(isNaN) ||
        parts[0] + parts[1] !== 100
      ) {
        alert('Enter two numbers that sum to 100 (e.g. 30/70).');
        return;
      }
      const parent = li.parentElement;
      li.remove();  // remove the original slot
      parts.forEach(cap => {
        const newLi = document.createElement('li');
        newLi.className = 'draggable-resource';
        newLi.draggable = true;
        newLi.dataset.id       = el.dataset.id;
        newLi.dataset.capacity = cap;
        if (el.dataset.typeId)  newLi.dataset.typeId  = el.dataset.typeId;
        if (el.dataset.groupId) newLi.dataset.groupId = el.dataset.groupId;
        // reuse the inner HTML but swap out the capacity
        newLi.innerHTML = originalHTML.replace(/\d+%/, `${cap}%`);
        parent.appendChild(newLi);
        setupResource(newLi);
      });
    });
  }

  // initialize all pool items
  document.querySelectorAll('.draggable-resource').forEach(el => {
    if (!el.dataset.capacity) el.dataset.capacity = '100';
    setupResource(el);
  });

  // ─── Project dropzones ────────────────────────────────────────────
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
        body: JSON.stringify({ sprint_id: sprintId, project_id: projId, resource_id: resId, capacity })
      });
      window.location.reload();
    });
  });

  // ─── Unassign buttons ─────────────────────────────────────────────
  document.querySelectorAll('.unassign-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const zone     = btn.closest('.project-dropzone');
      const sprintId = zone.closest('[data-sprint-id]').dataset.sprintId;
      await fetch('/unassign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprint_id: sprintId,
          project_id: zone.dataset.projectId,
          resource_id: btn.dataset.resourceId
        })
      });
      window.location.reload();
    });
  });

  // ─── FILTERING LOGIC ─────────────────────────────────────────────
  const typeCheckboxes  = Array.from(document.querySelectorAll('input.filter-type'));
  const groupCheckboxes = Array.from(document.querySelectorAll('input.filter-group'));

  function filterResources() {
    const selTypes  = typeCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
    const selGroups = groupCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
    document.querySelectorAll('#resource-pool .draggable-resource').forEach(li => {
      const tOK = !selTypes.length  || (li.dataset.typeId  && selTypes.includes(li.dataset.typeId));
      const gOK = !selGroups.length || (li.dataset.groupId && selGroups.includes(li.dataset.groupId));
      li.style.display = (tOK && gOK) ? '' : 'none';
    });
  }

  typeCheckboxes.forEach(cb => cb.addEventListener('change', filterResources));
  groupCheckboxes.forEach(cb => cb.addEventListener('change', filterResources));
  filterResources();
});
