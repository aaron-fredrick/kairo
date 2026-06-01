<script>
  import { createEventDispatcher } from 'svelte';
  import MessageCard from './MessageCard.svelte';
  import { uploadFile } from './api.js';

  export let rooms = [];
  export let selectedRoomId = null;
  export let allMessages = [];
  export let username = '';
  export let isLoadingMessages = false;
  export let currentMessage = '';
  export let activeUsers = [];

  const dispatch = createEventDispatcher();

  let chatHistoryRef = null;
  let fileInputRef = null;
  let pendingAttachments = [];    // Array of { upload_id, filename, mime_type, size_bytes }
  let uploadProgress = {};        // Map of file name -> percentage
  let isUploading = false;

  export function scrollToBottom() {
    if (chatHistoryRef) {
      setTimeout(() => {
        chatHistoryRef.scrollTop = chatHistoryRef.scrollHeight;
      }, 50);
    }
  }

  $: selectedRoom = rooms.find(r => r.id === selectedRoomId);
  $: admins = (activeUsers || []).filter(u => u.role === 'admin');
  $: mods = (activeUsers || []).filter(u => u.role === 'moderator');
  $: normals = (activeUsers || []).filter(u => u.role === 'normal');

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendClick();
    }
  }

  function handleSendClick() {
    dispatch('send', { attachments: pendingAttachments });
    pendingAttachments = [];
  }

  function triggerFilePicker() {
    fileInputRef?.click();
  }

  async function handleFileSelected(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    e.target.value = '';

    isUploading = true;
    try {
      const promises = files.map(async (file) => {
        uploadProgress[file.name] = 0;
        uploadProgress = uploadProgress;
        const data = await uploadFile(file, selectedRoomId, {
          onProgress: (pct) => {
            uploadProgress[file.name] = pct;
            uploadProgress = uploadProgress;
          },
        });
        delete uploadProgress[file.name];
        uploadProgress = uploadProgress;
        pendingAttachments = [...pendingAttachments, {
          upload_id: data.upload_id,
          filename: data.original_filename,
          mime_type: data.mime_type,
          size_bytes: data.size_bytes,
        }];
      });
      await Promise.all(promises);
    } catch (err) {
      console.error('Upload error:', err);
      alert(err.message);
    } finally {
      isUploading = false;
    }
  }

  function clearAttachment(index) {
    pendingAttachments = pendingAttachments.filter((_, i) => i !== index);
  }


  $: hasPendingAttachments = pendingAttachments.length > 0 || Object.keys(uploadProgress).length > 0;
</script>

<section class="chat-container">
  <div class="chat-main">
    <header class="chat-header">
    <div class="room-title">
      <h2>#{selectedRoom?.name || '...'}</h2>
      <p class="room-description">{selectedRoom?.description || ''}</p>
    </div>
    <div class="connection-status">
      <span class="status-dot"></span>
      Connected
    </div>
  </header>

  <div class="message-history" bind:this={chatHistoryRef}>
    {#if isLoadingMessages}
      <div class="skeleton-message">
        <div class="skeleton-avatar skeleton"></div>
        <div class="skeleton-content">
          <div class="skeleton-meta skeleton"></div>
          <div class="skeleton-text skeleton"></div>
          <div class="skeleton-text short skeleton"></div>
        </div>
      </div>
      <div class="skeleton-message">
        <div class="skeleton-avatar skeleton"></div>
        <div class="skeleton-content">
          <div class="skeleton-meta skeleton"></div>
          <div class="skeleton-text skeleton"></div>
        </div>
      </div>
    {:else}
      {#each allMessages as message (message.id)}
        <MessageCard {message} isSelf={message.sender === username} />
      {/each}
    {/if}
  </div>

  <!-- Pending attachment preview strip -->
  {#if hasPendingAttachments}
    <div class="attachment-preview-strip">
      {#each pendingAttachments as attachment, index}
        <div class="attachment-preview-inner">
          <span class="attachment-preview-icon">{attachment.mime_type?.startsWith('image/') ? '🖼️' : '📄'}</span>
          <span class="attachment-preview-name">{attachment.filename}</span>
          <button class="attachment-clear-btn" onclick={() => clearAttachment(index)} title="Remove attachment">✕</button>
        </div>
      {/each}
      {#each Object.entries(uploadProgress) as [filename, progress]}
        <div class="attachment-preview-inner uploading">
          <span class="attachment-preview-icon">⏳</span>
          <span class="attachment-preview-name">{filename} ({progress}%)</span>
        </div>
      {/each}
    </div>
  {/if}

  <form
    class="message-input-form"
    onsubmit={(e) => { e.preventDefault(); handleSendClick(); }}
  >
    <!-- Hidden native file input -->
    <input
      bind:this={fileInputRef}
      type="file"
      multiple
      class="hidden-file-input"
      onchange={handleFileSelected}
    />

    <button
      type="button"
      class="attachment-btn"
      class:uploading={isUploading}
      onclick={triggerFilePicker}
      title="Attach file"
      disabled={isUploading}
    >
      {isUploading ? '⌛' : '📎'}
    </button>

    <textarea
      bind:value={currentMessage}
      placeholder="Message #{selectedRoom?.name || '...'}..."
      rows="1"
      onkeydown={handleKeydown}
    ></textarea>

    <button
      type="submit"
      class="send-btn"
      disabled={(!currentMessage.trim() && pendingAttachments.length === 0) || isUploading}
    >Send</button>
  </form>
  </div>
  <aside class="members-sidebar">
    {#if admins.length > 0}
      <div class="role-group">
        <h3 class="role-header">Admins — {admins.length}</h3>
        {#each admins as u}
          <div class="member-item">
            <div class="member-avatar">
              {#if u.pfp_urls}
                <img src={u.pfp_urls['128']} alt={u.username} />
              {:else}
                <span>{u.username.charAt(0).toUpperCase()}</span>
              {/if}
            </div>
            <span class="member-name">{u.username}</span>
          </div>
        {/each}
      </div>
    {/if}

    {#if mods.length > 0}
      <div class="role-group">
        <h3 class="role-header">Mods — {mods.length}</h3>
        {#each mods as u}
          <div class="member-item">
            <div class="member-avatar">
              {#if u.pfp_urls}
                <img src={u.pfp_urls['128']} alt={u.username} />
              {:else}
                <span>{u.username.charAt(0).toUpperCase()}</span>
              {/if}
            </div>
            <span class="member-name">{u.username}</span>
          </div>
        {/each}
      </div>
    {/if}

    {#if normals.length > 0}
      <div class="role-group">
        <h3 class="role-header">Users — {normals.length}</h3>
        {#each normals as u}
          <div class="member-item">
            <div class="member-avatar">
              {#if u.pfp_urls}
                <img src={u.pfp_urls['128']} alt={u.username} />
              {:else}
                <span>{u.username.charAt(0).toUpperCase()}</span>
              {/if}
            </div>
            <span class="member-name">{u.username}</span>
          </div>
        {/each}
      </div>
    {/if}
  </aside>
</section>

<style>
  .chat-container {
    flex: 1;
    display: flex;
    flex-direction: row;
    background-color: #1e1e1e;
    overflow: hidden;
  }

  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .chat-header {
    height: 70px;
    padding: 0 1.5rem;
    border-bottom: 1px solid #333333;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .room-title h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
  }

  .room-description {
    margin: 0.2rem 0 0;
    font-size: 0.8rem;
    color: #6b7280;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #10b981;
    font-weight: 500;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .message-history {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  /* Pending attachment preview */
  .attachment-preview-strip {
    padding: 0.5rem 1.5rem;
    background: #252526;
    border-top: 1px solid #333333;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .attachment-preview-inner {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #3c3c3c;
    border-radius: 6px;
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
    color: #cccccc;
    max-width: 100%;
  }

  .attachment-preview-inner.uploading {
    background: #444;
    color: #aaa;
  }

  .attachment-preview-icon {
    font-size: 1rem;
    flex-shrink: 0;
  }

  .attachment-preview-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 260px;
  }

  .attachment-clear-btn {
    background: transparent;
    border: none;
    color: #858585;
    cursor: pointer;
    font-size: 0.85rem;
    padding: 0 0.2rem;
    line-height: 1;
    flex-shrink: 0;
    transition: color 0.15s;
  }

  .attachment-clear-btn:hover {
    color: #cccccc;
  }

  /* Form */
  .message-input-form {
    padding: 1.5rem;
    display: flex;
    gap: 0.75rem;
    border-top: 1px solid #333333;
    align-items: flex-end;
  }

  .hidden-file-input {
    display: none;
  }

  .message-input-form textarea {
    flex: 1;
    background-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    color: #cccccc;
    font-size: 0.95rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s ease;
    resize: none;
    max-height: 120px;
    overflow-y: auto;
  }

  .message-input-form textarea:focus {
    border-color: #007acc;
  }

  .attachment-btn {
    background: transparent;
    border: 1px solid #333333;
    color: #858585;
    border-radius: 8px;
    padding: 0 1rem;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 48px;
    flex-shrink: 0;
  }

  .attachment-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.05);
    color: #cccccc;
  }

  .attachment-btn.uploading {
    opacity: 0.6;
    cursor: wait;
  }

  .message-input-form .send-btn {
    background: #007acc;
    color: white;
    border: none;
    outline: none;
    border-radius: 8px;
    padding: 0 1.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
    height: 48px;
    flex-shrink: 0;
  }

  .message-input-form .send-btn:hover:not(:disabled) {
    opacity: 0.85;
  }

  .message-input-form .send-btn:disabled {
    background: #3c3c3c;
    color: #555555;
    cursor: not-allowed;
  }

  /* Skeleton loaders */
  @keyframes shimmer {
    0% { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }

  .skeleton {
    background: #333333;
    background-image: linear-gradient(90deg, #333333 0px, #3c3c3c 40px, #333333 80px);
    background-size: 800px 100%;
    animation: shimmer 2s infinite linear;
  }

  .skeleton-message {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }


  .skeleton-avatar {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .skeleton-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .skeleton-meta {
    height: 14px;
    width: 120px;
    border-radius: 4px;
  }

  .skeleton-text {
    height: 16px;
    width: 80%;
    border-radius: 4px;
  }

  .skeleton-text.short {
    width: 50%;
  }
  .members-sidebar {
    width: 240px;
    background-color: #252526;
    border-left: 1px solid #333333;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 1rem 0.5rem;
  }

  .role-group {
    margin-bottom: 1.5rem;
  }

  .role-header {
    font-size: 0.75rem;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 0 0 0.5rem 0.5rem;
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  .member-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    border-radius: 4px;
    cursor: default;
    transition: background-color 0.1s;
  }

  .member-item:hover {
    background-color: #2a2d31;
  }

  .member-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #3c3c3c;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .member-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .member-avatar span {
    color: white;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .member-name {
    font-size: 0.95rem;
    color: #e5e7eb;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
