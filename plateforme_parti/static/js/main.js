// Chargement dynamique des communes et sections
document.addEventListener('DOMContentLoaded', function() {
    const departementSelect = document.getElementById('departement_id');
    const communeSelect = document.getElementById('commune_id');
    const sectionSelect = document.getElementById('section_id');

    if (departementSelect) {
        departementSelect.addEventListener('change', function() {
            const departementId = this.value;

            if (departementId) {
                // Charger les communes
                fetch(`/api/communes/${departementId}`)
                    .then(response => response.json())
                    .then(data => {
                        communeSelect.innerHTML = '<option value="">Sélectionnez une commune</option>';
                        data.forEach(commune => {
                            communeSelect.innerHTML += `<option value="${commune.id}">${commune.nom}</option>`;
                        });
                        communeSelect.disabled = false;
                        sectionSelect.innerHTML = '<option value="">Sélectionnez d\'abord une commune</option>';
                        sectionSelect.disabled = true;
                    });
            } else {
                communeSelect.innerHTML = '<option value="">Sélectionnez d\'abord un département</option>';
                communeSelect.disabled = true;
                sectionSelect.innerHTML = '<option value="">Sélectionnez d\'abord une commune</option>';
                sectionSelect.disabled = true;
            }
        });
    }

    if (communeSelect) {
        communeSelect.addEventListener('change', function() {
            const communeId = this.value;

            if (communeId) {
                // Charger les sections
                fetch(`/api/sections/${communeId}`)
                    .then(response => response.json())
                    .then(data => {
                        sectionSelect.innerHTML = '<option value="">Sélectionnez une section</option>';
                        data.forEach(section => {
                            sectionSelect.innerHTML += `<option value="${section.id}">${section.nom}</option>`;
                        });
                        sectionSelect.disabled = false;
                    });
            } else {
                sectionSelect.innerHTML = '<option value="">Sélectionnez d\'abord une commune</option>';
                sectionSelect.disabled = true;
            }
        });
    }
});

// Gestion des messages et notifications
class MessageManager {
    constructor() {
        this.checkInterval = null;
        this.init();
    }

    init() {
        // Démarrer la vérification des messages si l'utilisateur est connecté
        if (document.querySelector('.user-menu')) {
            this.startMessageCheck();
            this.initMessageEvents();
        }
    }

    startMessageCheck() {
        // Vérifier les nouveaux messages toutes les 30 secondes
        this.checkInterval = setInterval(() => {
            this.checkNewMessages();
        }, 30000);
    }

    async checkNewMessages() {
        try {
            const response = await fetch('/api/messages/non_lus');
            const data = await response.json();

            if (data.count > 0) {
                this.updateNotificationBadge(data.count);
                this.showNotification(data.count);
            }
        } catch (error) {
            console.error('Erreur lors de la vérification des messages:', error);
        }
    }

    updateNotificationBadge(count) {
        let badge = document.querySelector('.unread-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'badge bg-danger ms-1 unread-badge';
            const messagesTab = document.querySelector('button[data-bs-target="#recus"]');
            if (messagesTab) {
                messagesTab.appendChild(badge);
            }
        }

        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    }

    showNotification(count) {
        if (Notification.permission === 'granted') {
            new Notification('Nouveaux messages', {
                body: `Vous avez ${count} nouveau${count > 1 ? 'x' : ''} message${count > 1 ? 's' : ''} non lu${count > 1 ? 's' : ''}`,
                icon: '/static/img/logo.png'
            });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }

    initMessageEvents() {
        // Marquer un message comme lu
        document.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const messageId = btn.dataset.messageId;
                await this.markAsRead(messageId);
                btn.closest('.message-item').classList.remove('unread');
                btn.remove();
            });
        });

        // Supprimer un message
        document.querySelectorAll('.delete-message-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (confirm('Voulez-vous vraiment supprimer ce message ?')) {
                    const messageId = btn.dataset.messageId;
                    await this.deleteMessage(messageId);
                    btn.closest('.message-item').remove();
                }
            });
        });
    }

    async markAsRead(messageId) {
        try {
            const response = await fetch(`/message/marquer-lu/${messageId}`);
            if (!response.ok) {
                throw new Error('Erreur lors du marquage');
            }
        } catch (error) {
            console.error('Erreur:', error);
        }
    }

    async deleteMessage(messageId) {
        try {
            const response = await fetch(`/message/supprimer/${messageId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la suppression');
            }

            showToast('Message supprimé avec succès', 'success');
        } catch (error) {
            console.error('Erreur:', error);
            showToast('Erreur lors de la suppression', 'danger');
        }
    }
}

// Initialiser le gestionnaire de messages
const messageManager = new MessageManager();