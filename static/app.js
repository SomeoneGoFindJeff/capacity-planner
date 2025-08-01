// static/app.js
document.addEventListener('DOMContentLoaded', () => {
  // ─── 1) Sprint–detail filters that “stick” ─────────────────────────────
  const sprintId   = document.querySelector('[data-sprint-id]')?.dataset?.sprintId;
  const typeBoxes  = Array.from(document.querySelectorAll('.filter-type'));
  const groupBoxes = Array.from(document.querySelectorAll('.filter-group'));

  function loadFilters() {
    if (!sprintId) return;
    const stored = JSON.parse(localStorage.getItem(`filters:${sprintId}`) || '{}');
    typeBoxes.forEach(cb => { cb.checked = stored.types?.includes(cb.value)  || false; });
    groupBoxes.forEach(cb =>{ cb.checked = stored.groups?.includes(cb.value) || false; });
  }
  function saveAndApplyFilters() {
    if (!sprintId) return;
    const selT = typeBoxes.filter(cb=>cb.checked).map(cb=>cb.value);
    const selG = groupBoxes.filter(cb=>cb.checked).map(cb=>cb.value);
    localStorage.setItem(`filters:${sprintId}`, JSON.stringify({types:selT,groups:selG}));

    document.querySelectorAll('#resource-pool .draggable-resource').forEach(li => {
      const tOK = !selT.length  || (li.dataset.typeId  && selT.includes(li.dataset.typeId));
      const gOK = !selG.length || (li.dataset.groupId && selG.includes(li.dataset.groupId));
      li.style.display = (tOK && gOK) ? '' : 'none';
    });
  }
  if (sprintId) {
    loadFilters();
    typeBoxes .forEach(cb => cb.addEventListener('change', saveAndApplyFilters));
    groupBoxes.forEach(cb => cb.addEventListener('change', saveAndApplyFilters));
    saveAndApplyFilters();
  }
  // Clear filters on page unload
  window.addEventListener('beforeunload', () => {
    if (sprintId) localStorage.removeItem(`filters:${sprintId}`);
  });

  // ─── 2) Unassign button ────────────────────────────────────────────────
  document.querySelectorAll('.unassign-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const zone = btn.closest('.project-dropzone');
      const sid  = zone.dataset.sprintId;
      const pid  = zone.dataset.projectId;
      const rid  = btn.dataset.resourceId;
      await fetch('/unassign', {
        method: 'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ sprint_id:sid, project_id:pid, resource_id:rid })
      });
      window.location.reload();
    });
  });

  // ─── 3) Resources page → Table + inline row‐edit ───────────────────────
  const tbl = document.getElementById('resources-table');
  if (tbl) {
    const types = JSON.stringify(JSON.parse(tbl.dataset.types));
    const groups = JSON.stringify(JSON.parse(tbl.dataset.groups));

    tbl.querySelector('tbody').addEventListener('click', ev => {
      const tr = ev.target.closest('tr');
      if (!tr) return;
      const rid = tr.dataset.resourceId;

      // Enter edit mode
      if (ev.target.closest('.edit-btn')) {
        const nameCell = tr.querySelector('.name-cell');
        const oldName  = nameCell.textContent.trim();
        nameCell.innerHTML = `<input class="input input-small edit-input" value="${oldName}"/>`;

        const typeCell = tr.querySelector('.type-cell');
        const curType  = tr.dataset.typeId || '';
        typeCell.innerHTML = `<select class="input input-small edit-type">${JSON.parse(types).map(t=>
          `<option value="${t.id}" ${t.id==curType?'selected':''}>${t.name}</option>`
        ).join('')}</select>`;

        const groupCell = tr.querySelector('.group-cell');
        const curGroup  = tr.dataset.groupId || '';
        groupCell.innerHTML = `<select class="input input-small edit-group">${JSON.parse(groups).map(g=>
          `<option value="${g.id}" ${g.id==curGroup?'selected':''}>${g.name}</option>`
        ).join('')}</select>`;

        tr.querySelector('.action-cell').innerHTML = `
          <button class="btn btn-secondary save-btn"><span class="material-icons">check</span></button>
          <button class="btn btn-secondary cancel-btn"><span class="material-icons">close</span></button>
        `;
      }

      // Cancel edit
      else if (ev.target.closest('.cancel-btn')) {
        window.location.reload();
      }

      // Save edit
      else if (ev.target.closest('.save-btn')) {
        const newName  = tr.querySelector('.edit-input').value;
        const newType  = tr.querySelector('.edit-type').value;
        const newGroup = tr.querySelector('.edit-group').value;
        fetch(`/resources/edit/${rid}`, {
          method: 'POST',
          headers:{ 'Content-Type':'application/x-www-form-urlencoded' },
          body:`name=${encodeURIComponent(newName)}&type_id=${encodeURIComponent(newType)}&group_id=${encodeURIComponent(newGroup)}`
        }).then(()=>window.location.reload());
      }

      // Delete row
      else if (ev.target.closest('.delete-btn')) {
        fetch(`/resources/delete/${rid}`,{ method:'POST' })
          .then(()=>window.location.reload());
      }
    });
  }
});
