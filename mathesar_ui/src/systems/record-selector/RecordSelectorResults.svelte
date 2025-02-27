<script lang="ts">
  import { onMount } from 'svelte';
  import type { ProcessedTableColumnMap } from '@mathesar/sections/table-view/utils';
  import { getTabularDataStoreFromContext } from '@mathesar/stores/table-data/tabularData';
  import type { Row } from '@mathesar/stores/table-data/records';
  import Cell from '@mathesar/components/cell/Cell.svelte';
  import RowCellBackgrounds from '@mathesar/sections/table-view/row/RowCellBackgrounds.svelte';
  import { rowHeightPx } from '@mathesar/sections/table-view/geometry';
  import CellArranger from './CellArranger.svelte';
  import CellWrapper from './CellWrapper.svelte';

  const tabularData = getTabularDataStoreFromContext();

  export let processedTableColumnsMap: ProcessedTableColumnMap;
  export let submit: (record: Row) => void;

  let selectionIndex = 0;

  $: ({ display } = $tabularData);
  $: recordsStore = $tabularData.recordsData.savedRecords;
  $: records = $recordsStore;
  $: rowWidthStore = display.rowWidth;
  $: rowWidth = $rowWidthStore;
  $: rowStyle = `width: ${rowWidth as number}px; height: ${rowHeightPx}px;`;

  function selectPrevious() {
    selectionIndex = Math.max(selectionIndex - 1, 0);
  }

  function selectNext() {
    selectionIndex = Math.min(selectionIndex + 1, records.length - 1);
  }

  function submitRecord(index: number) {
    submit(records[index]);
  }

  function handleKeydown(e: KeyboardEvent) {
    let handled = true;
    switch (e.key) {
      case 'ArrowUp':
        selectPrevious();
        break;
      case 'ArrowDown':
        selectNext();
        break;
      case 'Enter':
        submitRecord(selectionIndex);
        break;
      default:
        handled = false;
    }

    if (handled) {
      e.stopPropagation();
      e.preventDefault();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown, { capture: true });
    return () => {
      window.removeEventListener('keydown', handleKeydown, { capture: true });
    };
  });
</script>

<div class="record-selector-results">
  {#each records as row, index}
    {#if row.record}
      <div class="row" style={rowStyle} on:click={() => submitRecord(index)}>
        <CellArranger
          {processedTableColumnsMap}
          {display}
          let:style
          let:processedColumn
        >
          <CellWrapper {style}>
            <Cell
              sheetColumn={processedColumn}
              value={row.record[processedColumn.column.id]}
              disabled
            />
            <RowCellBackgrounds isSelected={index === selectionIndex} />
          </CellWrapper>
        </CellArranger>
      </div>
    {/if}
  {/each}
</div>

<style>
  .row {
    position: relative;
    cursor: pointer;
  }
  .row:not(:hover) :global(.cell-bg-row-hover) {
    display: none;
  }
</style>
