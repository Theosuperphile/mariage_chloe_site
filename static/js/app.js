(() => {
  const form = document.querySelector('#questionnaire');
  if (!form) return;
  const qPresence = document.querySelector('#questions-presence');
  const blocCouchages = document.querySelector('#bloc-couchages');
  const blocBrunch = document.querySelector('#bloc-brunch');
  const verification = document.querySelector('#verification-repas');
  const valeur = nom => form.querySelector(`input[name="${nom}"]:checked`)?.value;
  const nombre = id => Number(document.querySelector(`#${id}`)?.value || 0);

  function requisDans(bloc, actif) {
    bloc.querySelectorAll('input[type="radio"]').forEach(el => el.required = actif);
  }
  function actualiser() {
    const present = valeur('presence') === 'oui';
    qPresence.hidden = !present;
    requisDans(qPresence, present);
    const hebergement = present && valeur('hebergement') === 'oui';
    blocCouchages.hidden = !hebergement;
    document.querySelector('#couchages').required = hebergement;
    const brunch = present && valeur('brunch') === 'oui';
    blocBrunch.hidden = !brunch;
    ['brunch_adultes', 'brunch_enfants'].forEach(id => document.querySelector(`#${id}`).required = brunch);
    if (present) {
      const adultes = nombre('adultes');
      const repas = nombre('repas_classiques') + nombre('repas_vegetariens');
      const enfants = nombre('enfants');
      const menus = nombre('menus_enfants');
      const ok = adultes === repas && enfants === menus;
      verification.textContent = ok ? '✓ Les quantités de repas sont cohérentes.' : `À vérifier : ${adultes} adulte(s) pour ${repas} repas adulte(s), ${enfants} enfant(s) pour ${menus} menu(s) enfant.`;
      verification.className = `verification ${ok ? 'ok' : 'attention'}`;
    }
  }
  form.addEventListener('input', actualiser);
  form.addEventListener('change', actualiser);
  actualiser();
})();
