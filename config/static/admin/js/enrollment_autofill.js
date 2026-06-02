// Admin Enrollment : auto-remplit thinkific_user_id quand on sélectionne l'utilisateur.
// Le champ user utilise Select2 (Jazzmin) → l'event change est émis par jQuery,
// donc on bind via jQuery (et pas addEventListener natif qui ne le capterait pas).
(function () {
    'use strict';

    function endpointFor(uid) {
        var tkField = document.getElementById('id_thinkific_user_id');
        if (tkField && tkField.dataset && tkField.dataset.tkurl) {
            return tkField.dataset.tkurl.replace('__UID__', uid);
        }
        var marker = 'enrollment/';
        var path = window.location.pathname;
        var idx = path.indexOf(marker);
        if (idx === -1) return null;
        return path.substring(0, idx + marker.length) + 'thinkific-id/' + uid + '/';
    }

    function fill(uid) {
        var tkField = document.getElementById('id_thinkific_user_id');
        if (!tkField) return;
        if (!uid) { tkField.value = ''; return; }
        var url = endpointFor(uid);
        if (!url) return;
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                tkField.value = (d && d.thinkific_user_id) ? d.thinkific_user_id : '';
            })
            .catch(function () { /* silencieux */ });
    }

    function bind() {
        var $ = (window.django && window.django.jQuery) || window.jQuery;
        if ($) {
            // Délégation jQuery : capte aussi les change déclenchés par Select2
            $(document).on('change', '#id_user', function () { fill(this.value); });
        } else {
            // Fallback natif (si pas de Select2 / pas de jQuery)
            document.addEventListener('change', function (e) {
                if (e.target && e.target.id === 'id_user') fill(e.target.value);
            });
        }
        // Remplissage initial si un user est déjà sélectionné (page d'édition)
        var uf = document.getElementById('id_user');
        if (uf && uf.value) fill(uf.value);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
