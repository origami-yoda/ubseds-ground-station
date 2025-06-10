document.addEventListener('DOMContentLoaded', () => {
  // — VIEW SWITCHING —
  function showView(viewId) {
    document
      .querySelectorAll('#fill-view, #telemetry-view, #map-view, #buttons-view')
      .forEach(div => div.classList.add('hidden'));
    const v = document.getElementById(viewId);
    if (v) v.classList.remove('hidden');
  }

  const viewButtons = [
    ['btnFill',      'fill-view'],
    ['btnTelemetry', 'telemetry-view'],
    ['btnMap',       'map-view'],
    ['btnButtons',   'buttons-view']
  ];

  viewButtons.forEach(([btnId, viewId]) => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', () => showView(viewId));
    }
  });

  // default on load
  showView('telemetry-view');

  // — TOGGLE SWITCHES —
  // Helper to wire a toggle to a command
  function wireToggle(toggleId, onCmd, offCmd, label) {
    const tog = document.getElementById(toggleId);
    if (!tog) return;
    tog.addEventListener('change', e => {
      const cmd = e.target.checked ? onCmd : offCmd;
      console.log(`${label} ${e.target.checked ? 'ON' : 'OFF'} → "${cmd}"`);
      socket.emit('command', cmd);
    });
  }

  wireToggle('toggleSwitch1', 'e', 'r', 'N₂O valve');
  wireToggle('toggleSwitch2', 'q', 'w', 'N₂ valve');
  wireToggle('toggleSwitch3', 'i', 'o', 'Igniter');
  wireToggle('toggleSwitch4', 'a', 's', 'Normally Open');
  wireToggle('toggleSwitch5', 'd', 'f', 'Pilot Valve');

  // — TRI-STATE SLIDER —
  const triSwitch = document.getElementById('triSwitch');
  const triLabel  = document.getElementById('triLabel');
  if (triSwitch && triLabel) {
    triSwitch.addEventListener('input', e => {
      let cmd;
      switch (e.target.value) {
        case '1':
          triLabel.textContent = 'Forwards';
          cmd = 't';
          break;
        case '0':
          triLabel.textContent = 'Neutral';
          cmd = 'u';
          break;
        case '-1':
          triLabel.textContent = 'Backwards';
          cmd = 'y';
          break;
      }
      console.log(`Tri-State now ${triLabel.textContent} → "${cmd}"`);
      if (cmd) socket.emit('command', cmd);
    });
  }

  // — PROPULSION / TESTING MODE COMBINED CONTROL —
  const propulsionBtn     = document.getElementById('propulsionBtn');
  const pilotIgniterGroup = document.getElementById('pilotIgniterGroup');

  if (propulsionBtn && pilotIgniterGroup) {
    let propulsionActive = false;

    propulsionBtn.addEventListener('click', () => {
      propulsionActive = !propulsionActive;

      if (propulsionActive) {
        // Enter Testing Mode
        propulsionBtn.textContent = 'TESTING MODE';
        propulsionBtn.classList.remove('btn-danger');
        propulsionBtn.classList.add('btn-success');

        // Hide original Igniter & Pilot Valve switches
        ['toggleSwitch3', 'toggleSwitch4', 'toggleSwitch5'].forEach(id => {
          const el = document.getElementById(id);
          if (el && el.parentElement) el.parentElement.classList.add('hidden');
        });

        // Insert combined control UI
        pilotIgniterGroup.insertAdjacentHTML('beforeend', `
          <div id="combinedSwitchContainer" class="mt-3 d-flex align-items-center">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="combinedIgniterPilotSwitch" />
              <label class="form-check-label ms-2" for="combinedIgniterPilotSwitch">
                Igniter + Pilot Valve
              </label>
            </div>
            <input type="number" class="form-control ms-3" id="delayInputMs"
                   placeholder="Delay (ms)" style="width: 140px;">
          </div>
        `);

        // Wire combined logic
        const combinedSwitch = document.getElementById('combinedIgniterPilotSwitch');
        const delayInput     = document.getElementById('delayInputMs');
        if (combinedSwitch && delayInput) {
          combinedSwitch.addEventListener('change', async e => {
            const delayMs = parseInt(delayInput.value, 10) || 0;
            if (e.target.checked) {
              console.log(`Igniter ON → "i"`);
              socket.emit('command', 'i');
              await new Promise(resolve => setTimeout(resolve, delayMs));
              console.log(`Pilot Valve ON → "d"`);
              socket.emit('command', 'd');
            } else {
              console.log(`Igniter OFF → "o"`);
              socket.emit('command', 'o');
              console.log(`Pilot Valve OFF → "f"`);
              socket.emit('command', 'f');
            }
          });
        }

      } else {
        // Exit Testing Mode
        propulsionBtn.textContent = 'PROPULSION MODE';
        propulsionBtn.classList.remove('btn-success');
        propulsionBtn.classList.add('btn-danger');

        // Show original switches again
        ['toggleSwitch3', 'toggleSwitch4', 'toggleSwitch5'].forEach(id => {
          const el = document.getElementById(id);
          if (el && el.parentElement) el.parentElement.classList.remove('hidden');
        });

        // Remove combined UI if present
        const combined = document.getElementById('combinedSwitchContainer');
        if (combined) combined.remove();
      }
    });
  }
});
