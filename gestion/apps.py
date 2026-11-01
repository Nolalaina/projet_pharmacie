from django.apps import AppConfig


class GestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gestion"
    verbose_name = "Gestion de pharmacie"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .roles import initialiser_groupes

        post_migrate.connect(initialiser_groupes, sender=self, dispatch_uid="pharmagest_roles")
