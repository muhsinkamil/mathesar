<script lang="ts">
  import BaseInput from '@mathesar-component-library-dir/common/base-components/BaseInput.svelte';
  import type { TextInputProps } from './TextInputTypes';

  type $$Props = TextInputProps;

  /**
   * Value of the input. Use bind tag for two-way binding.
   * Refer Svelte docs for more info on binding form input values.
   */
  export let value: $$Props['value'] = '';

  // Additional classes
  let classes = '';
  export { classes as class };

  // Underlying DOM element for direct access
  export let element: $$Props['element'] = undefined;

  export let hasError = false;

  // Id for the input
  export let id: $$Props['id'] = undefined;
</script>

<BaseInput {...$$restProps} bind:id />

<input
  bind:this={element}
  {...$$restProps}
  type="text"
  class={['input-element', 'text-input', classes].join(' ')}
  class:has-error={hasError}
  bind:value
  {id}
  on:input
  on:focus
  on:blur
  on:keydown
  on:beforeinput
/>
