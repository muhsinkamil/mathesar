from bidict import bidict

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils.functional import cached_property
from django.contrib.auth.models import User

from db.columns import utils as column_utils
from db.columns.operations.create import create_column, duplicate_column
from db.columns.operations.alter import alter_column
from db.columns.operations.drop import drop_column
from db.columns.operations.select import get_column_name_from_attnum, get_columns_attnum_from_names
from db.constraints.operations.create import create_constraint
from db.constraints.operations.drop import drop_constraint
from db.constraints.operations.select import get_constraint_oid_by_name_and_table_oid, get_constraint_from_oid
from db.constraints import utils as constraint_utils
from db.records.operations.delete import delete_record
from db.records.operations.insert import insert_record_or_records
from db.records.operations.select import get_column_cast_records, get_count, get_record
from db.records.operations.select import get_records as db_get_records
from db.records.operations.update import update_record
from db.schemas.operations.drop import drop_schema
from db.schemas import utils as schema_utils
from db.tables import utils as table_utils
from db.tables.operations.drop import drop_table
from db.tables.operations.select import get_oid_from_table, reflect_table_from_oid
from db.tables.operations.split import extract_columns_from_table

from mathesar import reflection
from mathesar.utils import models as model_utils
from mathesar.database.base import create_mathesar_engine
from mathesar.database.types import UIType, get_ui_type_from_db_type


NAME_CACHE_INTERVAL = 60 * 5


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DatabaseObjectManager(models.Manager):
    def get_queryset(self):
        reflection.reflect_db_objects()
        return super().get_queryset()


class ReflectionManagerMixin(models.Model):
    """
    Used to reflect objects that exists on the user database but does not have a equivalent mathesar reference object.
    """
    # The default manager, current_objects, does not reflect database objects.
    # This saves us from having to deal with Django trying to automatically reflect db
    # objects in the background when we might not expect it.
    current_objects = models.Manager()
    objects = DatabaseObjectManager()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__}"


class DatabaseObject(ReflectionManagerMixin, BaseModel):
    """
    Objects that can be referenced using a database identifier
    """
    oid = models.IntegerField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__}: {self.oid}"

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.oid}>'


# TODO: Replace with a proper form of caching
# See: https://github.com/centerofci/mathesar/issues/280
_engines = {}


class Database(ReflectionManagerMixin, BaseModel):
    current_objects = models.Manager()
    objects = DatabaseObjectManager()
    name = models.CharField(max_length=128, unique=True)
    deleted = models.BooleanField(blank=True, default=False)

    @property
    def _sa_engine(self):
        global _engines
        # We're caching this since the engine is used frequently.
        if self.name not in _engines:
            engine = create_mathesar_engine(self.name)
            _engines[self.name] = engine
            return engine
        else:
            engine = _engines[self.name]
            model_utils.ensure_cached_engine_ready(engine)
            return engine

    @property
    def supported_ui_types(self):
        """
        At the moment we don't actually filter our UIType set based on whether or not a UIType's
        constituent DB types are supported.
        """
        return UIType

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.name}, {self.id}'


class Schema(DatabaseObject):
    database = models.ForeignKey('Database', on_delete=models.CASCADE,
                                 related_name='schemas')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["oid", "database"], name="unique_schema")
        ]

    @property
    def _sa_engine(self):
        return self.database._sa_engine

    @cached_property
    def name(self):
        cache_key = f"{self.database.name}_schema_name_{self.oid}"
        try:
            schema_name = cache.get(cache_key)
            if schema_name is None:
                schema_name = schema_utils.get_schema_name_from_oid(
                    self.oid, self._sa_engine
                )
                cache.set(cache_key, schema_name, NAME_CACHE_INTERVAL)
            return schema_name
        # We catch this error, since it lets us decouple the cadence of
        # overall DB reflection from the cadence of cache expiration for
        # schema names.  Also, it makes it obvious when the DB layer has
        # been altered, as opposed to other reasons for a 404 when
        # requesting a schema.
        except TypeError:
            return 'MISSING'

    # TODO: This should check for dependencies once the depdency endpoint is implemeted
    @property
    def has_dependencies(self):
        return True

    def update_sa_schema(self, update_params):
        return model_utils.update_sa_schema(self, update_params)

    def delete_sa_schema(self):
        return drop_schema(self.name, self._sa_engine, cascade=True)

    def clear_name_cache(self):
        cache_key = f"{self.database.name}_schema_name_{self.oid}"
        cache.delete(cache_key)


class Table(DatabaseObject):
    # These are fields whose source of truth is in the model
    MODEL_FIELDS = ['import_verified']

    schema = models.ForeignKey('Schema', on_delete=models.CASCADE,
                               related_name='tables')
    import_verified = models.BooleanField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["oid", "schema"], name="unique_table")
        ]

    def validate_unique(self, exclude=None):
        # Ensure oid is unique on db level
        if Table.current_objects.filter(
            oid=self.oid, schema__database=self.schema.database
        ).exists():
            raise ValidationError("Table OID is not unique")
        super().validate_unique(exclude=exclude)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.validate_unique()
        super().save(*args, **kwargs)

    @cached_property
    def _sa_engine(self):
        return self.schema._sa_engine

    @cached_property
    def _sa_table(self):
        try:
            table = reflect_table_from_oid(
                self.oid, self.schema._sa_engine,
            )
        # We catch these errors, since it lets us decouple the cadence of
        # overall DB reflection from the cadence of cache expiration for
        # table names.  Also, it makes it obvious when the DB layer has
        # been altered, as opposed to other reasons for a 404 when
        # requesting a table.
        except (TypeError, IndexError):
            table = table_utils.get_empty_table("MISSING")
        return table

    @cached_property
    def _enriched_column_sa_table(self):
        return column_utils.get_enriched_column_table(
            self._sa_table, engine=self._sa_engine,
        )

    @cached_property
    def name(self):
        return self._sa_table.name

    @cached_property
    def sa_columns(self):
        return self._enriched_column_sa_table.columns

    @property
    def sa_constraints(self):
        return self._sa_table.constraints

    @property
    def sa_column_names(self):
        return self.sa_columns.keys()

    # TODO: This should check for dependencies once the depdency endpoint is implemeted
    @property
    def has_dependencies(self):
        return True

    def add_column(self, column_data):
        return create_column(
            self.schema._sa_engine,
            self.oid,
            column_data,
        )

    def alter_column(self, column_attnum, column_data):
        return alter_column(
            self.schema._sa_engine,
            self.oid,
            column_attnum,
            column_data,
        )

    def drop_column(self, column_attnum):
        drop_column(
            self.oid,
            column_attnum,
            self.schema._sa_engine,
        )

    def duplicate_column(self, column_attnum, copy_data, copy_constraints, name=None):
        return duplicate_column(
            self.oid,
            column_attnum,
            self.schema._sa_engine,
            new_column_name=name,
            copy_data=copy_data,
            copy_constraints=copy_constraints,
        )

    def get_preview(self, column_definitions):
        return get_column_cast_records(
            self.schema._sa_engine, self._sa_table, column_definitions
        )

    @property
    def sa_all_records(self):
        return db_get_records(self._sa_table, self.schema._sa_engine)

    def sa_num_records(self, filter=None):
        return get_count(self._sa_table, self.schema._sa_engine, filter=filter)

    def update_sa_table(self, update_params):
        return model_utils.update_sa_table(self, update_params)

    def delete_sa_table(self):
        return drop_table(self.name, self.schema.name, self.schema._sa_engine, cascade=True)

    def get_record(self, id_value):
        return get_record(self._sa_table, self.schema._sa_engine, id_value)

    def get_records(
        self,
        limit=None,
        offset=None,
        filter=None,
        order_by=[],
        group_by=None,
        duplicate_only=None,
    ):
        return db_get_records(
            self._sa_table,
            self.schema._sa_engine,
            limit,
            offset,
            filter=filter,
            order_by=order_by,
            group_by=group_by,
            duplicate_only=duplicate_only,
        )

    def create_record_or_records(self, record_data):
        return insert_record_or_records(self._sa_table, self.schema._sa_engine, record_data)

    def update_record(self, id_value, record_data):
        return update_record(self._sa_table, self.schema._sa_engine, id_value, record_data)

    def delete_record(self, id_value):
        return delete_record(self._sa_table, self.schema._sa_engine, id_value)

    def add_constraint(self, constraint_obj):
        create_constraint(
            self._sa_table.schema,
            self.schema._sa_engine,
            constraint_obj
        )
        try:
            # Clearing cache so that new constraint shows up.
            del self._sa_table
        except AttributeError:
            pass
        engine = self.schema.database._sa_engine
        name = constraint_obj.name
        if not name:
            name = constraint_utils.get_constraint_name(engine, constraint_obj.constraint_type(), self.oid, constraint_obj.columns_attnum[0])
        constraint_oid = get_constraint_oid_by_name_and_table_oid(name, self.oid, engine)
        return Constraint.current_objects.create(oid=constraint_oid, table=self)

    def get_column_name_id_bidirectional_map(self):
        # TODO: Prefetch column names to avoid N+1 queries
        columns = Column.objects.filter(table_id=self.id)
        columns_map = bidict({column.name: column.id for column in columns})
        return columns_map

    def get_columns_by_name(self, name_list):
        columns_by_name_dict = {
            col.name: col
            for col
            in Column.objects.filter(table=self)
            if col.name in name_list
        }
        return [
            columns_by_name_dict[col_name]
            for col_name
            in name_list
        ]

    def split_table(
            self,
            columns_to_extract,
            extracted_table_name,
            remainder_table_name,
            drop_original_table
    ):
        columns_name_to_extract = [column.name for column in columns_to_extract]
        return extract_columns_from_table(
            self.name,
            columns_name_to_extract,
            extracted_table_name,
            remainder_table_name,
            self.schema.name,
            self._sa_engine,
            drop_original_table=drop_original_table
        )

    def update_column_reference(self, columns_name, column_name_id_map):
        columns_name_attnum_map = get_columns_attnum_from_names(
            self.oid,
            columns_name,
            self._sa_engine,
            return_as_name_map=True
        )
        column_objs = []
        for column_name, column_attnum in columns_name_attnum_map.items():
            column_id = column_name_id_map[column_name]
            column = Column.current_objects.get(id=column_id)
            column.table_id = self.id
            column.attnum = column_attnum
            column_objs.append(column)
        Column.current_objects.bulk_update(column_objs, fields=['table_id', 'attnum'])

    def insert_records_to_existing_table(existing_table, temp_table, mappings):
        # TBD
        pass


class Column(ReflectionManagerMixin, BaseModel):
    table = models.ForeignKey('Table', on_delete=models.CASCADE, related_name='columns')
    attnum = models.IntegerField()
    display_options = JSONField(null=True, default=None)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.table_id}-{self.attnum}"

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return getattr(self._sa_column, name)

    @property
    def _sa_engine(self):
        return self.table._sa_engine

    # TODO probably shouldn't be private: a lot of code already references it.
    @cached_property
    def _sa_column(self):
        return self.table.sa_columns[self.name]

    @property
    def name(self):
        return get_column_name_from_attnum(
            self.table.oid, self.attnum, self._sa_engine,
        )

    @property
    def ui_type(self):
        if self.db_type:
            return get_ui_type_from_db_type(self.db_type)

    @property
    def db_type(self):
        return self._sa_column.db_type


class Constraint(DatabaseObject):
    table = models.ForeignKey('Table', on_delete=models.CASCADE, related_name='constraints')

    @cached_property
    def _sa_constraint(self):
        engine = self.table.schema.database._sa_engine
        return get_constraint_from_oid(self.oid, engine, self.table._sa_table)

    @property
    def name(self):
        return self._sa_constraint.name

    @property
    def type(self):
        return constraint_utils.get_constraint_type_from_class(self._sa_constraint)

    @cached_property
    def columns(self):
        column_names = [column.name for column in self._sa_constraint.columns]
        engine = self.table.schema.database._sa_engine
        column_attnum_list = [result for result in get_columns_attnum_from_names(self.table.oid, column_names, engine)]
        return Column.objects.filter(table=self.table, attnum__in=column_attnum_list).order_by("attnum")

    @cached_property
    def referent_columns(self):
        if self.type == constraint_utils.ConstraintType.FOREIGN_KEY.value:
            column_names = [fk.column.name for fk in self._sa_constraint.elements]
            engine = self.table.schema._sa_engine
            oid = get_oid_from_table(self._sa_constraint.referred_table.name,
                                     self._sa_constraint.referred_table.schema,
                                     engine)
            table = Table.objects.get(oid=oid, schema=self.table.schema)
            column_attnum_list = get_columns_attnum_from_names(oid, column_names, table.schema._sa_engine)
            columns = Column.objects.filter(table=table, attnum__in=column_attnum_list).order_by("attnum")
            return columns
        return None

    @cached_property
    def ondelete(self):
        if self.type == constraint_utils.ConstraintType.FOREIGN_KEY.value:
            return self._sa_constraint.ondelete

    @cached_property
    def onupdate(self):
        if self.type == constraint_utils.ConstraintType.FOREIGN_KEY.value:
            return self._sa_constraint.onupdate

    @cached_property
    def deferrable(self):
        if self.type == constraint_utils.ConstraintType.FOREIGN_KEY.value:
            return self._sa_constraint.deferrable

    @cached_property
    def match(self):
        if self.type == constraint_utils.ConstraintType.FOREIGN_KEY.value:
            return self._sa_constraint.match

    def drop(self):
        drop_constraint(
            self.table._sa_table.name,
            self.table._sa_table.schema,
            self.table.schema._sa_engine,
            self.name
        )
        self.delete()


class DataFile(BaseModel):
    created_from_choices = models.TextChoices("created_from", "FILE PASTE URL")

    file = models.FileField(upload_to=model_utils.user_directory_path)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    created_from = models.CharField(max_length=128, choices=created_from_choices.choices)
    table_imported_to = models.ForeignKey(Table, related_name="data_files", blank=True,
                                          null=True, on_delete=models.SET_NULL)

    base_name = models.CharField(max_length=100)
    header = models.BooleanField(default=True)
    delimiter = models.CharField(max_length=1, default=',', blank=True)
    escapechar = models.CharField(max_length=1, blank=True)
    quotechar = models.CharField(max_length=1, default='"', blank=True)
