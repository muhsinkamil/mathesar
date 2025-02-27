# Generated by Django 3.1.14 on 2022-06-29 14:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mathesar', '0028_query'),
    ]

    operations = [
        migrations.CreateModel(
            name='UIQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=128, null=True, unique=True)),
                ('initial_columns', models.JSONField()),
                ('transformations', models.JSONField(blank=True, null=True)),
                ('display_options', models.JSONField(blank=True, null=True)),
                ('base_table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mathesar.table')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.DeleteModel(
            name='Query',
        ),
    ]
