<script lang="ts">
  import { dayjs, isDefinedNonNullable } from '@mathesar-component-library';
  import { createEventDispatcher } from 'svelte';
  import {
    FormattedInput,
    InlineDateTimePicker,
    AttachableDropdown,
  } from '@mathesar-component-library';
  import type {
    DateTimeCellExternalProps,
    DateTimeCellProps,
  } from '../typeDefinitions';

  const dispatch = createEventDispatcher();

  type $$Props = DateTimeCellExternalProps & {
    value: DateTimeCellProps['value'];
  };

  export let type: $$Props['type'];
  export let formattingString: $$Props['formattingString'];
  export let formatter: $$Props['formatter'];

  export let value: $$Props['value'];
  export let timeShow24Hr: $$Props['timeShow24Hr'] = true;
  export let timeEnableSeconds: $$Props['timeEnableSeconds'] = true;

  let element: HTMLInputElement;
  let isOpen = false;

  function getDatePickerValue(_value: $$Props['value']): string | undefined {
    if (isDefinedNonNullable(_value)) {
      const parsedAndFormatted = formatter.parseAndFormat(_value);
      if (dayjs(parsedAndFormatted, formattingString, true).isValid()) {
        return parsedAndFormatted;
      }
    }
    return undefined;
  }

  $: datePickerValue = getDatePickerValue(value);

  function open() {
    isOpen = true;
  }

  function close() {
    isOpen = false;
  }

  function checkAndBlur() {
    // check if clicked entry is on dropdown and then send event accordingly
    if (!isOpen) {
      dispatch('blur');
    }
  }

  function onDropdownClose() {
    dispatch('blur');
  }

  function onValueChange(newValue: string) {
    value = formatter.parse(newValue).value;
    close();
  }
</script>

<FormattedInput
  focusOnMount={true}
  bind:value
  {formatter}
  placeholder={formattingString}
  bind:element
  on:focus={open}
  on:focus
  on:blur={checkAndBlur}
  on:keydown
/>

<AttachableDropdown
  class="retain-active-cell no-max-height"
  trigger={element}
  bind:isOpen
  on:close={onDropdownClose}
>
  <InlineDateTimePicker
    {type}
    value={datePickerValue}
    format={formattingString}
    {timeShow24Hr}
    {timeEnableSeconds}
    on:change={(e) => onValueChange(e.detail)}
  />
</AttachableDropdown>
