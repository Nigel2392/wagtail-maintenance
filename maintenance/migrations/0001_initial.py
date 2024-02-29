# Generated by Django 4.2 on 2023-12-08 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PermissionOnlyModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Maintenance Permission Model',
                'verbose_name_plural': 'Maintenance Permission Models',
                'permissions': (('toggle_mainenance_mode', 'Can toggle maintenance mode'), ('see_menu_item', 'Can see menu item')),
                'managed': False,
                'default_permissions': (),
            },
        ),
    ]