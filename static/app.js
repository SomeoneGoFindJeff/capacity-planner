// static/app.js

document.addEventListener('DOMContentLoaded', () => {
  // ─── 1) Sprint‐detail filters that “stick” ─────────────────────────────
  const sprintDetail = document.querySelector('.sprint-detail-section');
  if (sprintDetail) {
    const sprintId   = sprintDetail.querySelector('[data-sprint-id]')?.dataset?.sprintId;
    const typeBoxes  = Array.from(document.querySelectorAll('.filter-type'));
    const groupBoxes = Array.from(document.querySelectorAll('.filter-group'));

    function loadFilters() {
      if (!sprintId) return;
      const stored = JSON.parse(localStorage.getItem(`filters:${sprintId}`) || '{}');
      typeBoxes.forEach(cb => { cb.checked = stored.types?.includes(cb.value) || false; });
      groupBoxes.forEach(cb => { cb.checked = stored.groups?.includes(cb.value) || false; });
    }

    function saveAndApplyFilters() {
      if (!sprintId) return;
      const selT = typeBoxes.filter(cb => cb.checked).map(cb => cb.value);
      const selG = groupBoxes.filter(cb => cb.checked).map(cb => cb.value);
      localStorage.setItem(`filters:${sprintId}`, JSON.stringify({ types: selT, groups: selG }));

      document.querySelectorAll('#resource-pool .draggable-resource').forEach(li => {
        const tOK = !selT.length || (li.dataset.typeId && selT.includes(li.dataset.typeId));
        const gOK = !selG.length || (li.dataset.groupId && selG.includes(li.dataset.groupId));
        li.style.display = (tOK && gOK) ? '' : 'none';
      });
    }

    loadFilters();
    typeBoxes.forEach(cb => cb.addEventListener('change', saveAndApplyFilters));
    groupBoxes.forEach(cb => cb.addEventListener('change', saveAndApplyFilters));
    saveAndApplyFilters();

    // Clear filters on navigate away
    window.addEventListener('beforeunload', () => {
      if (sprintId) localStorage.removeItem(`filters:${sprintId}`);
    });

    // ─── Drag & Drop ─────────────────────────────────────────────
    function setupResource(el) {
      el.addEventListener('dragstart', ev => {
        ev.dataTransfer.setData('text/plain', el.dataset.id);
        ev.dataTransfer.setData('application/capacity', el.dataset.capacity);
      });
    }

    document.querySelectorAll('#resource-pool .draggable-resource').forEach(el => {
      if (!el.dataset.capacity) el.dataset.capacity = '100';
      setupResource(el);
    });

    document.querySelectorAll('.project-dropzone').forEach(zone => {
      zone.addEventListener('dragover', ev => { ev.preventDefault(); zone.classList.add('dragover'); });
      zone.addEventListener('dragleave', () => { zone.classList.remove('dragover'); });
      zone.addEventListener('drop', async ev => {
        ev.preventDefault();
        zone.classList.remove('dragover');
        const resId    = ev.dataTransfer.getData('text/plain');
        const capacity = ev.dataTransfer.getData('application/capacity');
        const projId   = zone.dataset.projectId;
        const sprintId = zone.dataset.sprintId;
        await fetch('/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sprint_id: sprintId, project_id: projId, resource_id: resId, capacity })
        });
        window.location.reload();
      });
    });

    // ─── Unassign ─────────────────────────────────────────────────
    document.querySelectorAll('.unassign-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const zone     = btn.closest('.project-dropzone');
        const sid      = zone.dataset.sprintId;
        const pid      = zone.dataset.projectId;
        const rid      = btn.dataset.resourceId;
        await fetch('/unassign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sprint_id: sid, project_id: pid, resource_id: rid })
        });
        window.location.reload();
      });
    });
  }

  // ─── 2) Resources page → Table + inline row‐edit ───────────────────────
  const resourcesTable = document.getElementById('resources-table');
  if (resourcesTable) {
    resourcesTable.querySelector('tbody').addEventListener('click', ev => {
      const tr = ev.target.closest('tr');
      if (!tr) return;
      const rid = tr.dataset.resourceId;

      if (ev.target.closest('.edit-btn')) {
        // ... existing inline edit code for resources ...
      } else if (ev.target.closest('.save-btn')) {
        // ... save logic ...
      } else if (ev.target.closest('.cancel-btn')) {
        window.location.reload();
      } else if (ev.target.closest('.delete-btn')) {
        fetch(`/resources/delete/${rid}`, { method: 'POST' }).then(() => window.location.reload());
      }
    });
  }

  // ─── 3) Types page → inline row‐edit & delete ─────────────────────────
  const typesTable = document.querySelector('table[data-type-id]');
  if (typesTable) {
    typesTable.querySelector('tbody').addEventListener('click', ev => {
      const tr = ev.target.closest('tr'); if (!tr) return;
      const tid = tr.dataset.typeId;
      if (ev.target.closest('.edit-btn')) {
        const nameCell = tr.querySelector('.name-cell');
        const oldName = nameCell.textContent.trim();
        nameCell.innerHTML = `<input class="input input-small edit-input" value="${oldName}"/>`;
        tr.querySelector('.action-cell').innerHTML = `
          <button class="btn btn-secondary save-btn"><span class="material-icons">check</span></button>
          <button class="btn btn-secondary cancel-btn"><span class="material-icons">close</span></button>
        `;
      } else if (ev.target.closest('.save-btn')) {
        const newName = tr.querySelector('.edit-input').value;
        fetch(`/types/edit/${tid}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `name=${encodeURIComponent(newName)}`
        }).then(() => window.location.reload());
      } else if (ev.target.closest('.cancel-btn')) {
        window.location.reload();
      } else if (ev.target.closest('.delete-btn')) {
        fetch(`/types/delete/${tid}`, { method: 'POST' }).then(() => window.location.reload());
      }
    });
  }

  // ─── 4) Groups page → inline row‐edit & delete ────────────────────────
  const groupsTable = document.querySelector('table[data-group-id]');
  if (groupsTable) {
    groupsTable.querySelector('tbody').addEventListener('click', ev => {
      const tr = ev.target.closest('tr'); if (!tr) return;
      const gid = tr.dataset.groupId;
      if (ev.target.closest('.edit-btn')) {
        const nameCell = tr.querySelector('.name-cell');
        const oldName = nameCell.textContent.trim();
        nameCell.innerHTML = `<input class="input input-small edit-input" value="${oldName}"/>`;
        tr.querySelector('.action-cell').innerHTML = `
          <button class="btn btn-secondary save-btn"><span class="material-icons">check</span></button>
          <button class="btn btn-secondary cancel-btn"><span class="material-icons">close</span></button>
        `;
      } else if (ev.target.closest('.save-btn')) {
        const newName = tr.querySelector('.edit-input').value;
        fetch(`/groups/edit/${gid}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `name=${encodeURIComponent(newName)}`
        }).then(() => window.location.reload());
      } else if (ev.target.closest('.cancel-btn')) {
        window.location.reload();
      } else if (ev.target.closest('.delete-btn')) {
        fetch(`/groups/delete/${gid}`, { method: 'POST' }).then(() => window.location.reload());
      }
    });
  }
});
