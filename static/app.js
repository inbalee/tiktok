let searchMode = "username";
let commentState = { videoId: "", cursor: 0, hasMore: false };
let lastVideoMetadata = null;

function formatNumber(num) {
  if (num === null || num === undefined || num === "") return "-";
  return Number(num).toLocaleString("en-US");
}

async function parseApiResponse(res) {
  const body = await res.json();
  if (!res.ok || body.success === false) {
    const message = body.error || "Something went wrong.";
    if (res.status === 503) {
      const retryAfter = Number(res.headers.get("Retry-After") || 5);
      throw new Error(`${message} Retry in about ${retryAfter}s.`);
    }
    throw new Error(message);
  }
  return body.data ?? body;
}

function setVisible(el, visible) {
  el.classList.toggle("hidden", !visible);
}

function setLoading(loading) {
  const btn = document.getElementById("search-btn");
  const btnText = btn.querySelector(".btn-text");
  const spinner = btn.querySelector(".btn-spinner");
  btn.disabled = loading;
  btnText.classList.toggle("hidden", loading);
  spinner.classList.toggle("hidden", !loading);
}

function showError(message) {
  document.getElementById("error-box").textContent = message;
  setVisible(document.getElementById("error-box"), true);
  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("keyword-results"), false);
  setVisible(document.getElementById("comment-results"), false);
  setVisible(document.getElementById("video-metadata-results"), false);
}

function hideError() {
  setVisible(document.getElementById("error-box"), false);
}

function hideAllResults() {
  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("keyword-results"), false);
  setVisible(document.getElementById("comment-results"), false);
  setVisible(document.getElementById("video-metadata-results"), false);
  setVisible(document.getElementById("profile-back"), false);
}

function updateSearchMode(mode) {
  searchMode = mode;
  const prefix = document.getElementById("input-prefix");
  const input = document.getElementById("search-input");

  document.querySelectorAll(".mode-btn").forEach((btn) => {
    const active = btn.dataset.mode === mode;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });

  if (mode === "username") {
    prefix.textContent = "@";
    setVisible(prefix, true);
    input.placeholder = "username";
  } else if (mode === "keyword") {
    setVisible(prefix, false);
    input.placeholder = "Search keyword";
  } else if (mode === "videolink") {
    setVisible(prefix, false);
    input.placeholder = "Paste TikTok video link";
  } else {
    setVisible(prefix, false);
    input.placeholder = "Video ID or URL for comments";
  }

  input.value = "";
  hideError();
  hideAllResults();
  input.focus();
}

function renderProfile(data, showBack = false) {
  document.getElementById("avatar").src = data.profile_pic || "";
  document.getElementById("avatar").alt = `${data.nickname || data.username} profile picture`;
  document.getElementById("nickname").textContent = data.nickname || data.username;
  document.getElementById("username-display").textContent = `@${data.username}`;

  const bio = document.getElementById("biography");
  if (data.biography) {
    bio.textContent = data.biography;
    setVisible(bio, true);
  } else {
    bio.textContent = "";
    setVisible(bio, false);
  }

  setVisible(document.getElementById("verified-badge"), data.verified);
  setVisible(document.getElementById("private-badge"), data.private_account);

  const regionBadge = document.getElementById("region-badge");
  if (data.region) {
    regionBadge.textContent = data.region;
    setVisible(regionBadge, true);
  } else {
    setVisible(regionBadge, false);
  }

  document.getElementById("stat-followers").textContent = formatNumber(data.followers);
  document.getElementById("stat-following").textContent = formatNumber(data.following);
  document.getElementById("stat-likes").textContent = formatNumber(data.likes);
  document.getElementById("stat-videos").textContent = formatNumber(data.videos);
  document.getElementById("detail-user-id").textContent = data.user_id || "-";
  document.getElementById("detail-friends").textContent = formatNumber(data.friend_count);
  document.getElementById("detail-heart").textContent = formatNumber(data.heart);
  document.getElementById("detail-digg").textContent = formatNumber(data.digg_count);

  const socialSection = document.getElementById("social-section");
  const socialList = document.getElementById("social-links");
  socialList.innerHTML = "";

  if (data.social_links && data.social_links.length > 0) {
    data.social_links.forEach((link) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = link.url;
      a.textContent = link.label;
      a.target = link.url.startsWith("mailto:") ? "_self" : "_blank";
      a.rel = "noopener noreferrer";
      li.appendChild(a);
      socialList.appendChild(li);
    });
    setVisible(socialSection, true);
  } else {
    setVisible(socialSection, false);
  }

  document.getElementById("profile-link").href = data.profile_url;
  setVisible(document.getElementById("profile-back"), showBack);
  setVisible(document.getElementById("keyword-results"), false);
  setVisible(document.getElementById("comment-results"), false);
  setVisible(document.getElementById("video-metadata-results"), false);
  setVisible(document.getElementById("results"), true);
}

function renderKeywordResults(data) {
  const userCount = data.users.length;
  const videoCount = (data.videos || []).length;
  const parts = [];
  if (userCount) parts.push(`${userCount} user${userCount === 1 ? "" : "s"}`);
  if (videoCount) parts.push(`${videoCount} video${videoCount === 1 ? "" : "s"}`);

  document.getElementById("keyword-results-title").textContent =
    `Results for "${data.keyword}"`;
  document.getElementById("keyword-results-count").textContent =
    parts.join(" · ") || "No results";

  const usersEl = document.getElementById("keyword-users");
  usersEl.innerHTML = "";

  data.users.forEach((user) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "user-result";

    const avatar = document.createElement("img");
    avatar.className = "user-result-avatar";
    avatar.src = user.profile_pic || "";
    avatar.alt = "";

    const body = document.createElement("div");
    body.className = "user-result-body";

    const top = document.createElement("div");
    top.className = "user-result-top";

    const name = document.createElement("span");
    name.className = "user-result-name";
    name.textContent = user.nickname || user.username;
    top.appendChild(name);

    if (user.verified) {
      const badge = document.createElement("span");
      badge.className = "user-result-verified";
      badge.textContent = "\u2713";
      top.appendChild(badge);
    }

    const handle = document.createElement("p");
    handle.className = "user-result-handle";
    handle.textContent = `@${user.username}`;

    body.appendChild(top);
    body.appendChild(handle);

    if (user.biography) {
      const bio = document.createElement("p");
      bio.className = "user-result-bio";
      bio.textContent = user.biography;
      body.appendChild(bio);
    }

    const stats = document.createElement("div");
    stats.className = "user-result-stats";

    [
      [user.followers, "Followers"],
      [user.likes, "Likes"],
      [user.videos, "Videos"],
    ].forEach(([value, label]) => {
      const block = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = formatNumber(value);
      block.appendChild(strong);
      block.append(label);
      stats.appendChild(block);
    });

    btn.appendChild(avatar);
    btn.appendChild(body);
    btn.appendChild(stats);
    btn.addEventListener("click", () => loadUserProfile(user.username, true));
    usersEl.appendChild(btn);
  });

  renderVideoSection(data.videos || []);
  renderTagSection("keyword-hashtags-section", "keyword-hashtags", data.hashtags, "views");
  renderTagSection("keyword-sounds-section", "keyword-sounds", data.sounds, "videos");

  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("comment-results"), false);
  setVisible(document.getElementById("video-metadata-results"), false);
  setVisible(document.getElementById("profile-back"), false);
  setVisible(document.getElementById("keyword-results"), true);
}

function formatDateTime(timestamp) {
  if (!timestamp) return "-";
  return new Date(Number(timestamp) * 1000).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderVideoMetadata(data) {
  lastVideoMetadata = data;

  const cover = document.getElementById("video-meta-cover");
  cover.src = data.cover || "";
  cover.alt = data.title || "Video cover";

  const duration = document.getElementById("video-meta-duration");
  if (data.duration) {
    duration.textContent = formatDuration(data.duration);
    setVisible(duration, true);
  } else {
    setVisible(duration, false);
  }

  document.getElementById("video-meta-title").textContent = data.title || "Untitled video";

  const avatar = document.getElementById("video-meta-avatar");
  avatar.src = data.author_avatar || "";
  avatar.alt = data.nickname || data.username || "Author";

  const authorLink = document.getElementById("video-meta-author");
  authorLink.textContent = data.username ? `@${data.username}` : "Unknown author";
  authorLink.href = data.profile_url || data.video_url;

  const nickname = document.getElementById("video-meta-nickname");
  if (data.nickname) {
    nickname.textContent = data.nickname;
    setVisible(nickname, true);
  } else {
    nickname.textContent = "";
    setVisible(nickname, false);
  }

  document.getElementById("video-meta-plays").textContent = formatNumber(data.play_count);
  document.getElementById("video-meta-likes").textContent = formatNumber(data.likes);
  document.getElementById("video-meta-comments").textContent = formatNumber(data.comment_count);
  document.getElementById("video-meta-shares").textContent = formatNumber(data.share_count);
  document.getElementById("video-meta-id").textContent = data.video_id || "-";
  document.getElementById("video-meta-author-id").textContent = data.author_id || "-";
  document.getElementById("video-meta-region").textContent = data.region || "-";
  document.getElementById("video-meta-created").textContent = formatDateTime(data.create_time);
  document.getElementById("video-meta-downloads").textContent = formatNumber(data.download_count);
  document.getElementById("video-meta-saves").textContent = formatNumber(data.collect_count);

  const musicSection = document.getElementById("video-meta-music-section");
  const musicText = document.getElementById("video-meta-music");
  if (data.music_title) {
    musicText.textContent = data.music_author
      ? `${data.music_title} — ${data.music_author}`
      : data.music_title;
    setVisible(musicSection, true);
  } else {
    musicText.textContent = "";
    setVisible(musicSection, false);
  }

  document.getElementById("video-meta-open").href = data.video_url;
  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("keyword-results"), false);
  setVisible(document.getElementById("comment-results"), false);
  setVisible(document.getElementById("profile-back"), false);
  setVisible(document.getElementById("video-metadata-results"), true);
}

async function loadVideoMetadata(videoInput) {
  hideError();
  setLoading(true);

  try {
    const res = await fetch(`/api/video/metadata?url=${encodeURIComponent(videoInput)}`);
    renderVideoMetadata(await parseApiResponse(res));
  } catch (err) {
    showError(err.message || "Network error. Please try again.");
  } finally {
    setLoading(false);
  }
}

function extractVideoId(input) {
  const match = input.match(/\/video\/(\d+)/);
  if (match) return match[1];
  if (/^\d+$/.test(input)) return input;
  return input;
}

function appendCommentItem(comment) {
  const item = document.createElement("article");
  item.className = "comment-item";

  const userRow = document.createElement("div");
  userRow.className = "comment-user";

  const userLink = document.createElement("a");
  userLink.className = "comment-username";
  userLink.href = comment.profile_url || "#";
  userLink.target = "_blank";
  userLink.rel = "noopener noreferrer";
  userLink.textContent = `@${comment.username}`;

  if (comment.nickname) {
    const nickname = document.createElement("span");
    nickname.className = "comment-nickname";
    nickname.textContent = comment.nickname;
    userLink.appendChild(nickname);
  }

  const meta = document.createElement("div");
  meta.className = "comment-meta";

  const date = document.createElement("span");
  date.className = "comment-date";
  date.textContent = formatDateTime(comment.create_time);

  const likes = document.createElement("span");
  likes.className = "comment-likes";
  likes.textContent = `${formatNumber(comment.likes)} likes`;

  meta.appendChild(date);
  meta.appendChild(likes);

  userRow.appendChild(userLink);
  userRow.appendChild(meta);

  const text = document.createElement("p");
  text.className = "comment-text";
  text.textContent = comment.text;

  item.appendChild(userRow);
  item.appendChild(text);
  document.getElementById("comment-list").appendChild(item);
}

function renderCommentResults(data, append = false) {
  commentState = {
    videoId: data.video_id,
    cursor: data.cursor,
    hasMore: data.has_more,
  };

  if (!append) {
    document.getElementById("comment-list").innerHTML = "";
    document.getElementById("comment-results-title").textContent =
      `Comments for video ${data.video_id}`;
    document.getElementById("comment-results-meta").textContent =
      `${formatNumber(data.total)} total comments`;
    document.getElementById("comment-video-link").href = data.video_url;
  }

  data.comments.forEach(appendCommentItem);

  setVisible(document.getElementById("load-more-comments"), data.has_more);
  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("keyword-results"), false);
  setVisible(document.getElementById("video-metadata-results"), false);
  setVisible(document.getElementById("profile-back"), false);
  setVisible(document.getElementById("comment-results"), true);
}

async function loadVideoComments(videoInput, append = false) {
  hideError();
  const videoId = append ? commentState.videoId : extractVideoId(videoInput);

  if (!append) {
    setLoading(true);
  } else {
    const btn = document.getElementById("load-more-comments");
    btn.disabled = true;
    btn.textContent = "Loading...";
  }

  try {
    const cursor = append ? commentState.cursor : 0;
    const res = await fetch(
      `/api/video/${encodeURIComponent(videoId)}/comments?cursor=${cursor}&count=50`
    );
    renderCommentResults(await parseApiResponse(res), append);
  } catch (err) {
    showError(err.message || "Network error. Please try again.");
  } finally {
    if (!append) {
      setLoading(false);
    } else {
      const btn = document.getElementById("load-more-comments");
      btn.disabled = false;
      btn.textContent = "Load more comments";
    }
  }
}

function formatDuration(seconds) {
  const total = Number(seconds) || 0;
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function renderVideoSection(videos) {
  const section = document.getElementById("keyword-videos-section");
  const list = document.getElementById("keyword-videos");
  list.innerHTML = "";

  if (!videos.length) {
    setVisible(section, false);
    return;
  }

  videos.forEach((video) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "video-result";

    const coverWrap = document.createElement("div");
    coverWrap.className = "video-result-cover-wrap";

    if (video.cover) {
      const cover = document.createElement("img");
      cover.className = "video-result-cover";
      cover.className = "video-result-cover";
      cover.src = video.cover;
      cover.alt = "";
      coverWrap.appendChild(cover);
    }

    if (video.duration) {
      const duration = document.createElement("span");
      duration.className = "video-result-duration";
      duration.textContent = formatDuration(video.duration);
      coverWrap.appendChild(duration);
    }

    const body = document.createElement("div");
    body.className = "video-result-body";

    const title = document.createElement("p");
    title.className = "video-result-title";
    title.textContent = video.title || "Untitled video";

    const author = document.createElement("a");
    author.className = "video-result-author";
    author.href = video.username ? `https://www.tiktok.com/@${video.username}` : video.video_url;
    author.target = "_blank";
    author.rel = "noopener noreferrer";
    author.textContent = video.username ? `@${video.username}` : "View video";
    author.addEventListener("click", (e) => e.stopPropagation());

    const stats = document.createElement("div");
    stats.className = "video-result-stats";
    stats.innerHTML = `
      <span><strong>${formatNumber(video.play_count)}</strong> views</span>
      <span><strong>${formatNumber(video.likes)}</strong> likes</span>
      <span><strong>${formatNumber(video.comment_count)}</strong> comments</span>
    `;

    body.appendChild(title);
    body.appendChild(author);
    body.appendChild(stats);

    btn.appendChild(coverWrap);
    btn.appendChild(body);
    btn.addEventListener("click", () => loadVideoComments(video.video_id, false));
    list.appendChild(btn);
  });

  setVisible(section, true);
}

function renderTagSection(sectionId, listId, items, subKey) {
  const section = document.getElementById(sectionId);
  const list = document.getElementById(listId);
  list.innerHTML = "";

  if (items.length > 0) {
    items.forEach((item) => {
      const a = document.createElement("a");
      a.className = "tag-chip";
      a.href = item.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";

      const title = document.createElement("span");
      title.textContent = item.title;
      const sub = document.createElement("span");
      sub.textContent = item[subKey];

      a.appendChild(title);
      a.appendChild(sub);
      list.appendChild(a);
    });
    setVisible(section, true);
  } else {
    setVisible(section, false);
  }
}

async function loadUserProfile(username, fromKeyword = false) {
  hideError();
  setLoading(true);

  try {
    const res = await fetch(`/api/user/${encodeURIComponent(username)}`);
    renderProfile(await parseApiResponse(res), fromKeyword);
  } catch (err) {
    showError(err.message || "Network error. Please try again.");
  } finally {
    setLoading(false);
  }
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => updateSearchMode(btn.dataset.mode));
});

document.getElementById("profile-back").addEventListener("click", () => {
  setVisible(document.getElementById("results"), false);
  setVisible(document.getElementById("profile-back"), false);
  setVisible(document.getElementById("keyword-results"), true);
});

document.getElementById("load-more-comments").addEventListener("click", () => {
  if (commentState.videoId) {
    loadVideoComments(commentState.videoId, true);
  }
});

document.getElementById("video-meta-view-comments").addEventListener("click", () => {
  if (lastVideoMetadata?.video_id) {
    loadVideoComments(lastVideoMetadata.video_id, false);
  }
});

document.getElementById("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  const input = document.getElementById("search-input");
  const query = input.value.trim();
  if (!query) {
    const messages = {
      username: "Please enter a username.",
      keyword: "Please enter a keyword.",
      videolink: "Please enter a TikTok video link.",
      video: "Please enter a video ID or URL.",
    };
    showError(messages[searchMode] || "Please enter a search term.");
    return;
  }

  setLoading(true);

  try {
    if (searchMode === "username") {
      await loadUserProfile(query.replace(/^@/, ""), false);
    } else if (searchMode === "keyword") {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      renderKeywordResults(await parseApiResponse(res));
    } else if (searchMode === "videolink") {
      await loadVideoMetadata(query);
    } else {
      await loadVideoComments(query, false);
    }
  } catch (err) {
    showError(err.message || "Network error. Please try again.");
  } finally {
    setLoading(false);
  }
});
