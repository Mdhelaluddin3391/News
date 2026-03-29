from django.apps import AppConfig

class NewsConfig(AppConfig):
    name = 'news'

    def ready(self):
        # Yahan hum signals ko import kar rahe hain taaki Django app start hote hi inhe memory me load kar le
        import news.signals