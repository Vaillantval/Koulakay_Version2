// Admin Enrollment : auto-remplit thinkific_user_id quand on sélectionne l'utilisateur.
(function () {
    function init() {
        var userField = document.getElementById('id_user');
        var tkField = document.getElementById('id_thinkific_user_id');
        if (!userField || !tkField) return;

        // Construire l'URL de l'endpoint à partir du chemin courant (.../enrollment/...)
        var marker = 'enrollment/';
        var path = window.location.pathname;
        var idx = path.indexOf(marker);
        if (idx === -1) return;
        var base = path.substring(0, idx + marker.length);

        function fill() {
            var uid = userField.value;
            if (!uid) { tkField.value = ''; return; }
            fetch(base + 'thinkific-id/' + uid + '/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    tkField.value = (d && d.thinkific_user_id) ? d.thinkific_user_id : '';
                })
                .catch(function () { /* silencieux */ });
        }

        userField.addEventListener('change', fill);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
