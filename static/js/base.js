/**
 * Scripts communs pour base.html
 * 
 * Contient :
 * - Toggle de visibilité des mots de passe (bouton œil)
 * - Switch de thème clair/sombre
 * - Chargement paresseux du guide utilisateur
 */

document.addEventListener('DOMContentLoaded', function () {

    // ========================================================
    // 1. Password Toggle (bouton œil sur les champs password)
    // ========================================================
    const passwordInputs = document.querySelectorAll('input[type="password"]');

    passwordInputs.forEach(function (input) {
        // Ne pas traiter les inputs déjà dans un conteneur toggle
        if (input.parentElement.classList.contains('password-toggle-container')) {
            return;
        }

        // Créer un conteneur wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'password-toggle-container';

        // Remplacer l'input par le wrapper contenant l'input
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // Créer le bouton toggle
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle-btn';
        toggleBtn.innerHTML = '<i class="bi bi-eye"></i>';
        toggleBtn.setAttribute('aria-label', 'Afficher le mot de passe');

        // Ajouter le bouton au wrapper
        wrapper.appendChild(toggleBtn);

        // Ajouter l'événement de clic
        toggleBtn.addEventListener('click', function () {
            if (input.type === 'password') {
                input.type = 'text';
                toggleBtn.innerHTML = '<i class="bi bi-eye-slash"></i>';
                toggleBtn.setAttribute('aria-label', 'Masquer le mot de passe');
            } else {
                input.type = 'password';
                toggleBtn.innerHTML = '<i class="bi bi-eye"></i>';
                toggleBtn.setAttribute('aria-label', 'Afficher le mot de passe');
            }
        });
    });

    // ========================================================
    // 2. Theme Switch (clair / sombre)
    // ========================================================
    const themeSwitch = document.getElementById('themeSwitch');
    const themeIcon = document.getElementById('themeIcon');
    const html = document.documentElement;

    if (themeSwitch && themeIcon) {
        // Charger le thème sauvegardé
        const savedTheme = localStorage.getItem('gnmanager-theme') || 'light';
        if (savedTheme === 'dark') {
            themeSwitch.checked = true;
            themeIcon.className = 'bi bi-sun-fill';
        }

        // Gérer le changement de thème
        themeSwitch.addEventListener('change', function () {
            if (this.checked) {
                html.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('gnmanager-theme', 'dark');
                themeIcon.className = 'bi bi-sun-fill';
            } else {
                html.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('gnmanager-theme', 'light');
                themeIcon.className = 'bi bi-moon-fill';
            }
        });
    }

    // ========================================================
    // 3. Guide Modal (chargement paresseux)
    // ========================================================
    const guideModal = document.getElementById('guideModal');
    const guideContent = document.getElementById('guideContent');
    let guideLoaded = false;

    if (guideModal && guideContent) {
        const guideUrl = guideModal.getAttribute('data-guide-url');

        if (guideUrl) {
            guideModal.addEventListener('show.bs.modal', function () {
                if (!guideLoaded) {
                    fetch(guideUrl)
                        .then(response => response.text())
                        .then(html => {
                            guideContent.innerHTML = html;
                            guideLoaded = true;

                            // Make links open in new tab
                            guideContent.querySelectorAll('a').forEach(link => {
                                link.target = '_blank';
                            });
                        })
                        .catch(err => {
                            guideContent.innerHTML = '<div class="alert alert-danger">Impossible de charger le guide.</div>';
                            console.error('Erreur chargement guide:', err);
                        });
                }
            });
        }
    }
});
