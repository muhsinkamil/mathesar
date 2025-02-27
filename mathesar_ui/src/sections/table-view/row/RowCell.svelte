<script lang="ts">
  import { tick } from 'svelte';
  import { faBackspace } from '@fortawesome/free-solid-svg-icons';
  import {
    ContextMenu,
    MenuItem,
    WritableMap,
  } from '@mathesar-component-library';
  import {
    getCellStyle,
    isCellActive,
    ROW_CONTROL_COLUMN_WIDTH,
    scrollBasedOnActiveCell,
  } from '@mathesar/stores/table-data';
  import type {
    Row,
    Display,
    RecordsData,
    CellKey,
  } from '@mathesar/stores/table-data/types';
  import Cell from '@mathesar/components/cell/Cell.svelte';
  import Null from '@mathesar/components/Null.svelte';
  import type { RequestStatus } from '@mathesar/utils/api';
  import { States } from '@mathesar/utils/api';
  import CellErrors from './CellErrors.svelte';
  import type { ProcessedTableColumn } from '../utils';
  import CellBackground from './CellBackground.svelte';
  import RowCellBackgrounds from './RowCellBackgrounds.svelte';

  export let recordsData: RecordsData;
  export let display: Display;
  export let row: Row;
  export let rowIsSelected = false;
  export let rowIsProcessing = false;
  export let rowHasErrors = false;
  export let key: CellKey;
  export let modificationStatusMap: WritableMap<CellKey, RequestStatus>;
  export let processedColumn: ProcessedTableColumn;
  export let clientSideErrorMap: WritableMap<CellKey, string[]>;
  export let value: unknown = undefined;

  $: recordsDataState = recordsData.state;
  $: ({ column } = processedColumn);
  $: ({ activeCell, columnPlacements } = display);
  $: isActive = $activeCell && isCellActive($activeCell, row, column);
  $: modificationStatus = $modificationStatusMap.get(key);
  $: serverErrors =
    modificationStatus?.state === 'failure' ? modificationStatus?.errors : [];
  $: clientErrors = $clientSideErrorMap.get(key) ?? [];
  $: errors = [...serverErrors, ...clientErrors];
  $: canSetNull = column.nullable && value !== null;
  $: hasError = !!errors.length;
  $: isProcessing = modificationStatus?.state === 'processing';
  $: isEditable = !column.primary_key;

  async function checkTypeAndScroll(type?: string) {
    if (type === 'moved') {
      await tick();
      scrollBasedOnActiveCell();
    }
  }

  async function moveThroughCells(
    event: CustomEvent<{ originalEvent: KeyboardEvent; key: string }>,
  ) {
    const { originalEvent } = event.detail;
    const type = display.handleKeyEventsOnActiveCell(event.detail.key);
    if (type) {
      originalEvent.stopPropagation();
      originalEvent.preventDefault();

      await checkTypeAndScroll(type);
    }
  }

  async function setValue(newValue: unknown) {
    if (newValue === value) {
      return;
    }
    value = newValue;
    const updatedRow = row.isNew
      ? await recordsData.createOrUpdateRecord(row, column)
      : await recordsData.updateCell(row, column);
    value = updatedRow.record?.[column.id] ?? value;
  }

  async function valueUpdated(e: CustomEvent<{ value: unknown }>) {
    await setValue(e.detail.value);
  }
</script>

<div
  class="cell editable-cell"
  class:error={hasError}
  class:modified={modificationStatus?.state === 'success'}
  class:is-active={isActive}
  class:is-processing={isProcessing}
  class:is-pk={column.primary_key}
  style={getCellStyle($columnPlacements, column.id, ROW_CONTROL_COLUMN_WIDTH)}
>
  <CellBackground when={hasError} color="var(--cell-bg-color-error)" />
  <CellBackground when={!isEditable} color="var(--cell-bg-color-disabled)" />
  {#if !(isEditable && isActive)}
    <!--
      We hide these backgrounds when the cell is editable and active because a
      white background better communicates that the user can edit the active
      cell.
    -->
    <RowCellBackgrounds
      isSelected={rowIsSelected}
      isProcessing={rowIsProcessing}
      hasErrors={rowHasErrors}
    />
  {/if}

  <Cell
    sheetColumn={processedColumn}
    {isActive}
    {value}
    showAsSkeleton={$recordsDataState === States.Loading}
    disabled={!isEditable}
    on:movementKeyDown={moveThroughCells}
    on:activate={() => display.selectCell(row, column)}
    on:update={valueUpdated}
  />
  <ContextMenu>
    <MenuItem
      icon={{ data: faBackspace }}
      disabled={!canSetNull}
      on:click={() => setValue(null)}
    >
      Set to <Null />
    </MenuItem>
  </ContextMenu>
  {#if errors.length}
    <CellErrors {errors} forceShowErrors={isActive} />
  {/if}
</div>

<style lang="scss">
  .editable-cell.cell {
    user-select: none;
    position: relative;
    background: var(--cell-bg-color-base);

    &.is-active {
      z-index: 5;
      border: none;
      min-height: 100%;
      height: auto !important;
    }

    &.error,
    &.is-processing {
      color: var(--cell-text-color-processing);
    }
  }
</style>
