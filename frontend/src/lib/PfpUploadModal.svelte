<script>
  import { createEventDispatcher } from 'svelte';
  import { uploadPfp, confirmPfp } from './api.js';

  export let file;
  
  const dispatch = createEventDispatcher();
  
  let previewUrl = null;
  let isUploading = false;
  let error = null;
  
  $: if (file) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
  }

  async function uploadPfpAction() {
    isUploading = true;
    error = null;
    try {
      const preData = await uploadPfp(file);
      const confirmData = await confirmPfp(preData.pfp_upload_id);
      dispatch('success', confirmData.pfp_urls);
    } catch (err) {
      error = err.message;
    } finally {
      isUploading = false;
    }
  }
</script>

<div
  class="modal-backdrop"
  role="button"
  tabindex="0"
  on:click|self={() => !isUploading && dispatch('cancel')}
  on:keydown|self={(e) => e.key === 'Escape' && !isUploading && dispatch('cancel')}
>
  <div class="modal">
    <h2>Adjust Profile Picture</h2>
    <div class="preview-container">
      {#if previewUrl}
        <img src={previewUrl} alt="Preview" class="pfp-preview" />
      {/if}
    </div>
    {#if error}
      <div class="error">{error}</div>
    {/if}
    <div class="actions">
      <button class="cancel-btn" disabled={isUploading} on:click={() => dispatch('cancel')}>Cancel</button>
      <button class="update-btn" disabled={isUploading} on:click={uploadPfpAction}>
        {isUploading ? 'Updating...' : 'Update'}
      </button>
    </div>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  
  .modal {
    background: #252526;
    padding: 2rem;
    border-radius: 8px;
    width: 400px;
    max-width: 90%;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    border: 1px solid #3c3c3c;
  }
  
  h2 {
    margin: 0;
    color: #fff;
    font-size: 1.25rem;
    text-align: center;
  }
  
  .preview-container {
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  .pfp-preview {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #007acc;
  }
  
  .error {
    color: #f87171;
    font-size: 0.9rem;
    text-align: center;
    background: rgba(248, 113, 113, 0.1);
    padding: 0.5rem;
    border-radius: 4px;
  }
  
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
  }
  
  button {
    padding: 0.6rem 1.2rem;
    border-radius: 4px;
    border: none;
    font-weight: 600;
    cursor: pointer;
  }
  
  .cancel-btn {
    background: transparent;
    color: #cccccc;
  }
  
  .cancel-btn:hover {
    background: #333;
  }
  
  .update-btn {
    background: #007acc;
    color: white;
  }
  
  .update-btn:hover:not(:disabled) {
    background: #0098ff;
  }
  
  .update-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
