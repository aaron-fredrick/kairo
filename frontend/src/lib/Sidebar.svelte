<script>
  import { createEventDispatcher } from "svelte";

  import PfpUploadModal from "./PfpUploadModal.svelte";

  export let rooms = [];
  export let selectedRoomId = null;
  export let username = "";
  export let userRole = "normal";
  export let userPfpUrls = null;
  export let isLoadingRooms = true;

  const dispatch = createEventDispatcher();

  let fileInputRef;
  let selectedFile = null;

  function handleAvatarClick() {
    fileInputRef?.click();
  }

  function handleFileSelected(event) {
    const file = event.target.files[0];
    if (file) {
      selectedFile = file;
    }
    event.target.value = "";
  }
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <div class="logo">
      <span class="logo-icon">⚡</span>
      <h1>KAIRO</h1>
    </div>
  </div>

  <div class="section-title">CHANNELS</div>
  <nav class="room-list">
    {#if isLoadingRooms}
      <div class="skeleton-room skeleton"></div>
      <div class="skeleton-room skeleton"></div>
      <div class="skeleton-room skeleton"></div>
    {:else}
      {#each rooms as room (room.id)}
        <button
          class="room-item"
          class:active={room.id === selectedRoomId}
          onclick={() => dispatch("selectRoom", room.id)}
        >
          <span class="hash">#</span>
          <span class="room-name">{room.name}</span>
        </button>
      {/each}
    {/if}
  </nav>

  <div class="user-profile">
    <div
      class="avatar-container"
      onclick={handleAvatarClick}
      role="button"
      tabindex="0"
      onkeydown={(e) => e.key === "Enter" && handleAvatarClick()}
    >
      <div class="avatar" class:has-image={!!userPfpUrls}>
        {#if userPfpUrls}
          <img src={userPfpUrls["128"]} alt="PFP" class="avatar-img" />
        {:else}
          <span class="avatar-text">{username.slice(0, 2).toUpperCase()}</span>
        {/if}
        <div class="avatar-overlay">
          <span class="edit-icon">✎</span>
        </div>
        <span class="status-indicator online"></span>
      </div>
    </div>
    <div class="user-info">
      <span class="username">{username}</span>
      <span class="user-role"
        >{userRole === "admin"
          ? "Administrator"
          : userRole === "moderator"
            ? "Moderator"
            : "Guest User"}</span
      >
    </div>
  </div>
</aside>

<input
  bind:this={fileInputRef}
  type="file"
  accept="image/*"
  class="hidden-file-input"
  onchange={handleFileSelected}
/>

{#if selectedFile}
  <PfpUploadModal
    file={selectedFile}
    on:cancel={() => {
      selectedFile = null;
    }}
    on:success={(e) => {
      // The websocket 'pfp_updated' event will actually trigger the global update,
      // but we can proactively close the modal.
      selectedFile = null;
    }}
  />
{/if}

<style>
  .sidebar {
    width: 260px;
    background-color: #252526;
    border-right: 1px solid #333333;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid #333333;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-icon {
    font-size: 1.5rem;
    background: #007acc;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    color: #ffffff;
  }

  .logo h1 {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    margin: 0;
    color: #cccccc;
  }

  .section-title {
    padding: 1.5rem 1.5rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    color: #4b5563;
    letter-spacing: 0.1em;
  }

  .room-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .room-item {
    background: transparent;
    border: none;
    outline: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    color: #858585;
    border-radius: 8px;
    text-align: left;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
  }

  .room-item:hover {
    background-color: #2a2d2e;
    color: #cccccc;
  }

  .room-item.active {
    background-color: #37373d;
    color: #ffffff;
    font-weight: 600;
  }

  .hash {
    color: #858585;
    font-weight: 400;
  }

  .room-item.active .hash {
    color: #007acc;
  }

  .user-profile {
    padding: 1rem;
    background-color: #252526;
    border-top: 1px solid #333333;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .avatar-container {
    cursor: pointer;
    position: relative;
    border-radius: 50%;
  }

  .avatar {
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #007acc;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 0.9rem;
    color: white;
    overflow: hidden;
  }

  .avatar.has-image {
    background: transparent;
  }

  .avatar-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .avatar-container:hover .avatar-overlay {
    opacity: 1;
  }

  .edit-icon {
    font-size: 1rem;
    color: white;
  }

  .status-indicator {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #252526;
    z-index: 2;
  }

  .status-indicator.online {
    background-color: #10b981;
  }

  .user-info {
    display: flex;
    flex-direction: column;
  }

  .username {
    font-size: 0.9rem;
    font-weight: 600;
    color: #cccccc;
  }

  .user-role {
    font-size: 0.75rem;
    color: #6b7280;
  }

  /* Skeleton */
  @keyframes shimmer {
    0% {
      background-position: -400px 0;
    }
    100% {
      background-position: 400px 0;
    }
  }

  .skeleton {
    background: #333333;
    background-image: linear-gradient(
      90deg,
      #333333 0px,
      #3c3c3c 40px,
      #333333 80px
    );
    background-size: 800px 100%;
    animation: shimmer 2s infinite linear;
  }

  .skeleton-room {
    height: 38px;
    margin-bottom: 8px;
    border-radius: 8px;
  }

  .hidden-file-input {
    display: none;
  }
</style>
