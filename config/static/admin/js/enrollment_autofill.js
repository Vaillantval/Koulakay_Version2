// Admin Enrollment : auto-remplit thinkific_user_id quand on sélectionne l'utilisateur.
(function () {
    'use strict';

    function endpointFor(uid) {
        var tkField = document.getElementById('id_thinkific_user_id');
        // 1) URL fournie par le serveur via data-attribut (fiable)
        if (tkField && tkField.dataset && tkField.dataset.tkurl) {
            return tkField.dataset.tkurl.replace('__UID__', uid);
        }
        // 2) Fallback : déduire du chemin courant (.../enrollment/...)
        var marker = 'enrollment/';
        var path = window.location.pathname;
        var idx = path.indexOf(marker);
        if (idx === -1) return null;
        return path.substring(0, idx + marker.length) + 'thinkific-id/' + uid + '/';
    }

    function fill(uid) {
        var tkField = document.getElementById('id_thinkific_user_id');
        if (!tkField) { console.warn('[enroll-autofill] champ id_thinkific_user_id introuvable'); return; }
        if (!uid) { tkField.value = ''; return; }

        var url = endpointFor(uid);
        if (!url) { console.warn('[enroll-autofill] URL endpoint introuvable'); return; }
        console.log('[enroll-autofill] fetch', url);

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                console.log('[enroll-autofill] réponse', d);
                tkField.value = (d && d.thinkific_user_id) ? d.thinkific_user_id : '';
                if (!(d && d.thinkific_user_id)) {
                    console.warn('[enroll-autofill] cet utilisateur n a pas de thinkific_user_id');
                }
            })
            .catch(function (err) { console.error('[enroll-autofill] erreur fetch', err); });
    }

    // Délégation sur document : robuste même si le <select> est re-rendu
    document.addEventListener('change', function (e) {
        if (e.target && e.target.id === 'id_user') {
            fill(e.target.value);
        }
    });

    // Si un user est déjà sélectionné au chargement (édition), remplir aussi
    function initialFill() {
        var userField = document.getElementById('id_user');
        if (userField && userField.value) { fill(userField.value); }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialFill);
    } else {
        initialFill();
    }
})();
