import { get } from 'svelte/store';
import {
  currentDbAbstractTypes,
  getAbstractTypeForDbType,
} from '@mathesar/stores/abstract-types';
import type { AbstractTypeConfiguration } from '@mathesar/stores/abstract-types/types';
import type {
  ComponentAndProps,
  IconProps,
} from '@mathesar-component-library/types';
import type { Constraint } from '@mathesar/stores/table-data/constraints';
import { findFkConstraintsForColumn } from '@mathesar/stores/table-data/constraintsUtils';
import type { Column } from '@mathesar/stores/table-data/columns';
import DataTypes from './data-types';
import type { CellColumnLike } from './data-types/typeDefinitions';
import type { LinkedRecordCellExternalProps } from './data-types/components/typeDefinitions';
import LinkedRecordCell from './data-types/components/linked-record/LinkedRecordCell.svelte';

export type CellValueFormatter<T> = (
  value: T | null | undefined,
) => string | null | undefined;

function getCellInfo(
  dbType: CellColumnLike['type'],
): AbstractTypeConfiguration['cell'] | undefined {
  const abstractTypeOfColumn = getAbstractTypeForDbType(
    dbType,
    get(currentDbAbstractTypes)?.data,
  );
  return abstractTypeOfColumn?.cell;
}

function getCellConfiguration(
  dbType: CellColumnLike['type'],
  cellInfo?: AbstractTypeConfiguration['cell'],
): Record<string, unknown> {
  const config = cellInfo?.config ?? {};
  const conditionalConfig = cellInfo?.conditionalConfig?.[dbType] ?? {};
  return {
    ...config,
    ...conditionalConfig,
  };
}

export function getCellCap(
  column: Column,
  constraints: Constraint[],
  cellInfo: AbstractTypeConfiguration['cell'],
): ComponentAndProps<unknown> {
  const fks = findFkConstraintsForColumn(constraints, column.id);
  if (fks.length) {
    const props: LinkedRecordCellExternalProps = {
      tableId: fks[0].referent_table,
    };
    return {
      component: LinkedRecordCell,
      props,
    };
  }
  const config = getCellConfiguration(column.type, cellInfo);
  return DataTypes[cellInfo?.type ?? 'string'].get(column, config);
}

export function getDbTypeBasedInputCap(
  column: CellColumnLike,
  cellInfoConfig?: AbstractTypeConfiguration['cell'],
): ComponentAndProps<unknown> {
  const cellInfo = cellInfoConfig ?? getCellInfo(column.type);
  const config = getCellConfiguration(column.type, cellInfo);
  return DataTypes[cellInfo?.type ?? 'string'].getInput(column, config);
}

export function getColumnIconProps(column: CellColumnLike): IconProps {
  return getAbstractTypeForDbType(
    column.type,
    get(currentDbAbstractTypes)?.data,
  ).icon;
}
