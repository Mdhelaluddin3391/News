from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0011_article_is_web_story_article_web_story_created_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="article",
            index=GinIndex(
                SearchVector("title", weight="A", config="english")
                + SearchVector("description", weight="B", config="english")
                + SearchVector("content", weight="C", config="english"),
                name="article_fts_gin_idx",
            ),
        ),
    ]
