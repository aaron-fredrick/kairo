<script>
  export let message;
  export let isSelf;

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  $: attachments = message.attachments ?? [];

  let inlineEnlarged = {};
  let fullscreenAttachment = null;

  function toggleInlineEnlarge(blob_hash) {
    inlineEnlarged[blob_hash] = !inlineEnlarged[blob_hash];
  }

  function openFullscreen(attachment) {
    fullscreenAttachment = attachment;
  }

  function closeFullscreen(e) {
    if (e && e.target !== e.currentTarget) return;
    fullscreenAttachment = null;
  }

  let showPfpPopup = false;
  let pfpPopupUrls = null;

  function openPfpPopup(urls) {
    if (urls) {
      pfpPopupUrls = urls;
      showPfpPopup = true;
    }
  }

  function closePfpPopup(e) {
    if (e && e.target !== e.currentTarget) return;
    showPfpPopup = false;
    pfpPopupUrls = null;
  }
  
  let fullscreenPfp = null;
  function openFullscreenPfp(urls) {
    fullscreenPfp = urls;
  }
  function closeFullscreenPfp(e) {
    if (e && e.target !== e.currentTarget) return;
    fullscreenPfp = null;
  }
</script>

<div class="message-card" class:self={isSelf}>
  {#if !isSelf}
    {#if message.sender_pfp_urls}
      <button
        class="message-avatar clickable has-image"
        on:click={() => openPfpPopup(message.sender_pfp_urls)}
      >
        <img src={message.sender_pfp_urls['128']} alt="PFP" class="avatar-img" />
      </button>
    {:else}
      <div class="message-avatar">
        {message.sender.slice(0, 2).toUpperCase()}
      </div>
    {/if}
  {/if}

  <div class="message-content-wrapper">
    {#if isSelf}
      <div class="message-meta self-meta">
        <span class="message-time">{message.time}</span>
        {#if message.loading}
          <span class="message-status">
            <span class="loading-icon">⏳</span> Delivering...
          </span>
        {/if}
      </div>
    {:else}
      <div class="message-meta">
        <span class="message-sender">{message.sender}</span>
        <span class="message-time">{message.time}</span>
      </div>
    {/if}

    {#if message.content}
      <p class="message-text" class:pending={message.loading}>{message.content}</p>
    {/if}

    {#if attachments.length > 0}
      <div class="attachment-list">
        {#each attachments as attachment, i (attachment.attachment_id || i)}
          {@const isImage = attachment.mime_type?.startsWith('image/')}
          <div class="attachment-card">
            {#if isImage}
              {#if attachment.thumbnails_ready && attachment.thumbnails?.['128']}
                {@const isEnlarged = inlineEnlarged[attachment.blob_hash]}
                <div class="image-container">
                  <button
                    class="attachment-thumbnail-btn"
                    on:click={() => toggleInlineEnlarge(attachment.blob_hash)}
                  >
                    <img
                      class="attachment-thumbnail"
                      class:enlarged={isEnlarged}
                      src={isEnlarged ? attachment.thumbnails['512'] : attachment.thumbnails['128']}
                      alt={attachment.filename}
                    />
                  </button>
                  <a
                    class="image-download-overlay"
                    href={attachment.file_url}
                    download={attachment.filename}
                    on:click|stopPropagation
                    title="Download {attachment.filename}"
                  >↓</a>
                  {#if isEnlarged}
                    <button class="fullscreen-btn" on:click|stopPropagation={() => openFullscreen(attachment)}>⛶</button>
                  {/if}
                </div>
              {:else}
                <div class="attachment-placeholder">
                  <span class="attachment-icon">🖼️</span>
                  <div class="attachment-spinner"></div>
                  <span class="attachment-label">Generating preview…</span>
                </div>
              {/if}
            {:else}
              <div class="file-attachment">
                <span class="file-icon">📄</span>
                <div class="file-info">
                  <span class="file-name">{attachment.filename}</span>
                  <span class="file-size">{formatBytes(attachment.size_bytes)}</span>
                </div>
                <a
                  class="file-download"
                  href={attachment.file_url}
                  download={attachment.filename}
                  target="_blank"
                >↓</a>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

{#if fullscreenAttachment}
  <div
    class="fullscreen-overlay"
    role="presentation"
    on:click={closeFullscreen}
  >
    <img
      src={fullscreenAttachment.thumbnails['1024']}
      alt={fullscreenAttachment.filename}
    />
    <button class="close-btn" on:click={closeFullscreen}>×</button>
  </div>
{/if}

{#if showPfpPopup}
  <div
    class="pfp-popup-overlay"
    role="presentation"
    on:click={closePfpPopup}
  >
    <div
      class="pfp-popup-card"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
    >
      <div class="pfp-popup-header">
        <div
          class="pfp-popup-avatar-wrapper"
          role="button"
          tabindex="0"
          on:click={() => openFullscreenPfp(pfpPopupUrls)}
          on:keydown={(e) => e.key === 'Enter' && openFullscreenPfp(pfpPopupUrls)}
        >
          <img src={pfpPopupUrls['512']} alt="PFP Large" class="pfp-popup-img" />
          <div class="pfp-popup-hint">View Full</div>
        </div>
      </div>
      <div class="pfp-popup-body">
        <h3>{message.sender}</h3>
      </div>
    </div>
  </div>
{/if}

{#if fullscreenPfp}
  <div
    class="fullscreen-overlay"
    role="presentation"
    on:click={closeFullscreenPfp}
  >
    <img
      src={fullscreenPfp['1024']}
      alt="Fullscreen PFP"
    />
    <button class="close-btn" on:click={closeFullscreenPfp}>×</button>
  </div>
{/if}

<style>
  .message-card {
    display: flex;
    gap: 1rem;
    max-width: 80%;
  }

  .message-card.self {
    align-self: flex-end;
  }

  .message-card.self .message-content-wrapper {
    align-items: flex-end;
  }

  .message-card.self .attachment-list {
    align-items: flex-end;
  }

  .message-card.self .message-text {
    text-align: right;
  }

  .message-meta.self-meta {
    justify-content: flex-end;
  }

  .message-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #3c3c3c;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    color: #cccccc;
    flex-shrink: 0;
    overflow: hidden;
    padding: 0;
    border: none;
  }

  .message-avatar.has-image {
    background: transparent;
  }

  .message-avatar.clickable {
    cursor: pointer;
    transition: filter 0.2s;
  }

  .message-avatar.clickable:hover {
    filter: brightness(1.2);
  }

  .avatar-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .message-content-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .message-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .message-sender {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e5e7eb;
  }

  .message-time {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .message-text {
    margin: 0;
    font-size: 0.95rem;
    color: #d1d5db;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .message-text.pending {
    opacity: 0.6;
  }

  .message-status {
    font-size: 0.75rem;
    color: #f59e0b;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-weight: 500;
  }

  .loading-icon {
    font-size: 0.8rem;
    animation: spin 2s linear infinite;
  }

  @keyframes spin {
    100% { transform: rotate(360deg); }
  }

  /* Attachments */
  .attachment-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.15rem;
  }

  .attachment-card {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #333333;
    background: #252526;
    max-width: 512px;
    width: max-content;
  }

  .image-container {
    position: relative;
    display: inline-block;
    max-width: 100%;
    line-height: 0;
  }

  .attachment-thumbnail-btn {
    padding: 0;
    border: none;
    background: transparent;
    display: block;
  }

  .attachment-thumbnail {
    display: block;
    width: 128px;
    height: 128px;
    object-fit: cover;
    cursor: zoom-in;
    transition: opacity 0.2s;
  }

  .attachment-thumbnail.enlarged {
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 512px;
    cursor: zoom-out;
  }

  .attachment-thumbnail:hover {
    opacity: 0.9;
  }

  .fullscreen-btn {
    position: absolute;
    bottom: 0.5rem;
    right: 0.5rem;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    cursor: pointer;
    font-size: 1.25rem;
    opacity: 0;
    transition: opacity 0.2s;
    line-height: 1;
  }

  .fullscreen-btn:hover {
    background: rgba(0, 0, 0, 0.8);
  }

  .image-container:hover .fullscreen-btn {
    opacity: 1;
  }

  .image-download-overlay {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    font-weight: bold;
    text-decoration: none;
    opacity: 0;
    transition: opacity 0.2s, background 0.2s;
    line-height: 1;
  }

  .image-download-overlay:hover {
    background: rgba(0, 122, 204, 0.85);
  }

  .image-container:hover .image-download-overlay {
    opacity: 1;
  }

  .attachment-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 1.5rem;
    color: #858585;
    font-size: 0.85rem;
  }

  .attachment-icon {
    font-size: 1.75rem;
  }

  .attachment-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid #333333;
    border-top-color: #007acc;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .attachment-label {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .file-attachment {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
  }

  .file-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .file-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .file-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: #cccccc;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .file-size {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .file-download {
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    border-radius: 6px;
    background: #007acc;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    font-weight: bold;
    text-decoration: none;
    transition: opacity 0.2s;
  }

  .file-download:hover {
    opacity: 0.85;
  }

  /* Fullscreen Modal */
  .fullscreen-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(5px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .fullscreen-overlay img {
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  }

  .close-btn {
    position: absolute;
    top: 1.5rem;
    right: 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: white;
    font-size: 2rem;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    line-height: 1;
  }
  
  .close-btn:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  /* PFP Popup */
  .pfp-popup-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .pfp-popup-card {
    background: #1e1e24;
    border-radius: 8px;
    width: 300px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    border: 1px solid #333;
    overflow: hidden;
  }

  .pfp-popup-header {
    height: 120px;
    background: #007acc;
    position: relative;
    display: flex;
    align-items: flex-end;
    padding: 0 1rem;
  }

  .pfp-popup-avatar-wrapper {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    border: 6px solid #1e1e24;
    position: absolute;
    bottom: -50px;
    left: 1rem;
    cursor: pointer;
    background: #1e1e24;
    overflow: hidden;
  }

  .pfp-popup-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .pfp-popup-hint {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.6);
    color: white;
    font-size: 0.8rem;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .pfp-popup-avatar-wrapper:hover .pfp-popup-hint {
    opacity: 1;
  }

  .pfp-popup-body {
    padding: 60px 1rem 1rem;
  }

  .pfp-popup-body h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #fff;
  }
</style>
