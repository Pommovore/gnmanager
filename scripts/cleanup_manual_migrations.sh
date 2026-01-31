#!/bin/bash
#
# Script de nettoyage des migrations manuelles obsolètes
# À exécuter APRÈS avoir initialisé Flask-Migrate
#

set -e

echo "🧹 Nettoyage des scripts de migration manuels obsolètes"
echo "========================================================"
echo ""

# Créer un dossier d'archive temporaire
ARCHIVE_DIR="scripts/archive_manual_migrations_$(date +%Y%m%d)"
mkdir -p "$ARCHIVE_DIR"

echo "📁 Création du dossier d'archive: $ARCHIVE_DIR"
echo ""

# Liste des scripts à archiver
SCRIPTS_TO_ARCHIVE=(
    "scripts/add_association_field.py"
    "scripts/add_display_organizers_field.py"
    "scripts/add_eventlink_table.py"
    "scripts/add_paf_fields.py"
    "scripts/add_payment_methods.py"
    "scripts/add_theme_images.py"
)

echo "📦 Archivage des scripts de migration manuels..."
for script in "${SCRIPTS_TO_ARCHIVE[@]}"; do
    if [ -f "$script" ]; then
        echo "  ✓ Déplacement: $script"
        mv "$script" "$ARCHIVE_DIR/"
    else
        echo "  ⚠ Fichier non trouvé: $script"
    fi
done

echo ""
echo "🗑️  Suppression de l'ancien dossier archive..."
if [ -d "scripts/archive" ]; then
    rm -rf "scripts/archive"
    echo "  ✓ scripts/archive supprimé"
else
    echo "  ⚠ scripts/archive n'existe pas"
fi

echo ""
echo "✅ Nettoyage terminé !"
echo ""
echo "📋 Scripts conservés:"
ls -1 scripts/*.py scripts/*.sh 2>/dev/null || echo "  (aucun script Python/Shell restant)"
echo ""
echo "📦 Scripts archivés dans: $ARCHIVE_DIR"
ls -1 "$ARCHIVE_DIR" 2>/dev/null || echo "  (dossier vide)"
echo ""
echo "💡 Pour supprimer définitivement les archives plus tard:"
echo "   rm -rf $ARCHIVE_DIR"
