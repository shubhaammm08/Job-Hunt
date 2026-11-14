import os
import json

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="theme-color" content="#0d1117">
  <title>Shubham's JobHunt — Executive Dashboard</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text-main: #e6edf3;
      --text-muted: #8b949e;
      --accent-blue: #58a6ff;
      --accent-green: #238636;
      --green-light: #2ea043;
      --accent-purple: #bc8cff;
      --accent-amber: #d29922;
      --accent-red: #f85149;
      --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    html, body {
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font);
      min-height: 100vh;
      line-height: 1.5;
      overflow-x: hidden;
      width: 100%;
    }

    /* Container */
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px;
      padding-bottom: calc(50px + env(safe-area-inset-bottom, 0px));
    }

    /* Top Sticky Header */
    header {
      background: rgba(22, 27, 34, 0.95);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 4px 14px rgba(0,0,0,0.35);
      padding: max(10px, env(safe-area-inset-top, 10px)) 16px 10px 16px;
    }
    .header-content {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .brand-icon {
      font-size: 26px;
      flex-shrink: 0;
    }
    .brand-text {
      min-width: 0;
    }
    .brand h1 {
      font-size: 17px;
      font-weight: 800;
      letter-spacing: -0.2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .brand p {
      font-size: 11px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .cloud-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: rgba(35, 134, 54, 0.18);
      border: 1px solid rgba(46, 160, 67, 0.45);
      color: #3fb950;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 9px;
      border-radius: 999px;
      white-space: nowrap;
    }
    .cloud-pill .dot {
      width: 6px;
      height: 6px;
      background: #3fb950;
      border-radius: 50%;
      box-shadow: 0 0 6px #3fb950;
    }
    .btn-actions {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }

    /* Key Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin: 14px 0 16px 0;
    }
    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      transition: transform 0.1s ease;
    }
    .metric-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.4px;
      margin-bottom: 3px;
    }
    .metric-val {
      font-size: 24px;
      font-weight: 800;
      line-height: 1.15;
      color: var(--text-main);
    }
    .metric-sub {
      font-size: 11px;
      color: var(--accent-blue);
      margin-top: 2px;
    }

    /* Modern Navigation Tabs */
    .tabs-nav {
      display: flex;
      gap: 6px;
      background: rgba(22, 27, 34, 0.6);
      border: 1px solid var(--card-border);
      padding: 5px;
      border-radius: 10px;
      margin-bottom: 16px;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }
    .tabs-nav::-webkit-scrollbar { display: none; }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 14px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      border-radius: 7px;
      transition: all 0.15s ease;
      touch-action: manipulation;
    }
    .tab-btn:hover {
      color: var(--text-main);
    }
    .tab-btn.active {
      background: #21262d;
      color: #fff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .tab-badge {
      background: #30363d;
      color: var(--text-main);
      font-size: 11px;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 8px;
    }

    /* Tab Panels */
    .tab-panel { display: none; }
    .tab-panel.active { display: block; animation: fadeIn 0.2s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }

    /* Filters Section */
    .filters-section {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .search-row {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .search-box {
      flex: 1;
      position: relative;
    }
    .search-box input {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 10px 12px 10px 36px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.15s;
    }
    .search-box input:focus {
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
    }
    .search-icon {
      position: absolute;
      left: 11px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 14px;
      color: var(--text-muted);
      pointer-events: none;
    }

    /* Quick Filter Chips (1-touch on Mobile) */
    .chips-scroll {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
      padding-bottom: 2px;
    }
    .chips-scroll::-webkit-scrollbar { display: none; }
    .filter-chip {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 999px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
      touch-action: manipulation;
    }
    .filter-chip:hover { color: var(--text-main); }
    .filter-chip.active {
      background: rgba(88, 166, 255, 0.2);
      border-color: var(--accent-blue);
      color: #fff;
    }

    /* Detailed Dropdown Filters */
    .filter-selects {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }
    .select-filter {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 12.5px;
      outline: none;
      cursor: pointer;
    }
    .select-filter:focus { border-color: var(--accent-blue); }

    /* Results Bar */
    .results-count-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: var(--text-muted);
      padding: 0 4px 10px 4px;
    }

    /* Job Card Items */
    .job-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .job-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      transition: border-color 0.15s, transform 0.1s;
      position: relative;
    }
    .job-card:active {
      transform: scale(0.995);
    }
    .job-card.is-applied {
      border-left: 4px solid var(--accent-green);
      background: #11151a;
    }
    .job-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }
    .job-title-area {
      flex: 1;
      min-width: 0;
    }
    .job-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      line-height: 1.35;
      margin-bottom: 4px;
      word-break: break-word;
    }
    .job-meta-line {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 2px;
    }
    .job-company {
      font-size: 13.5px;
      color: var(--accent-blue);
      font-weight: 700;
    }
    .job-location {
      font-size: 12px;
      color: var(--text-muted);
    }
    .score-badge {
      font-size: 12px;
      font-weight: 800;
      padding: 3px 9px;
      border-radius: 999px;
      white-space: nowrap;
      flex-shrink: 0;
      align-self: flex-start;
    }
    .score-high {
      background: rgba(46, 160, 67, 0.2);
      border: 1px solid #3fb950;
      color: #3fb950;
    }
    .score-mid {
      background: rgba(88, 166, 255, 0.2);
      border: 1px solid #58a6ff;
      color: #58a6ff;
    }
    .score-low {
      background: rgba(139, 148, 158, 0.2);
      border: 1px solid #8b949e;
      color: #8b949e;
    }

    .job-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin: 10px 0 8px 0;
    }
    .tag {
      background: #21262d;
      border: 1px solid rgba(255,255,255,0.06);
      font-size: 11px;
      color: var(--text-muted);
      padding: 3px 8px;
      border-radius: 5px;
      white-space: nowrap;
    }
    .tag-family {
      background: rgba(188, 140, 255, 0.15);
      border: 1px solid rgba(188, 140, 255, 0.35);
      color: #d2a8ff;
      font-weight: 600;
    }
    .tag-source {
      background: rgba(210, 153, 34, 0.15);
      border: 1px solid rgba(210, 153, 34, 0.35);
      color: #e3b341;
      font-weight: 600;
    }

    .job-reason {
      font-size: 12.5px;
      color: #c9d1d9;
      background: rgba(0,0,0,0.3);
      border-radius: 8px;
      padding: 9px 12px;
      margin: 9px 0;
      border-left: 3px solid var(--accent-blue);
      line-height: 1.45;
    }

    /* Actions Bottom Bar */
    .job-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid rgba(48, 54, 61, 0.6);
      gap: 8px;
    }
    .job-date {
      font-size: 11px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .action-group {
      display: flex;
      gap: 8px;
      flex-shrink: 0;
    }
    .btn-applied {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-size: 12.5px;
      padding: 7px 12px;
      border-radius: 7px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s;
      touch-action: manipulation;
    }
    .btn-applied.active {
      background: rgba(46, 160, 67, 0.22);
      border-color: #3fb950;
      color: #3fb950;
      font-weight: 700;
    }
    .btn-apply-link {
      background: var(--accent-green);
      border: 1px solid rgba(255,255,255,0.1);
      color: #fff;
      font-size: 12.5px;
      padding: 7px 14px;
      border-radius: 7px;
      text-decoration: none;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.15s;
      white-space: nowrap;
      touch-action: manipulation;
    }
    .btn-apply-link:hover {
      background: var(--green-light);
    }

    /* Digest Panel */
    .digest-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      min-height: 600px;
    }
    .digest-frame {
      width: 100%;
      height: 750px;
      border: none;
      background: #0f1115;
    }

    /* Sources Grid */
    .sources-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 10px;
    }
    .source-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .source-info h4 { font-size: 13px; margin-bottom: 2px; }
    .source-info span { font-size: 11px; color: var(--text-muted); }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; }
    .status-healthy { background: #3fb950; box-shadow: 0 0 5px #3fb950; }
    .status-config { background: #d29922; }

    /* Profile Card */
    .profile-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px;
    }
    .profile-header {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 16px;
    }
    .avatar {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: #238636;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      flex-shrink: 0;
    }
    .p-group { margin-bottom: 16px; }
    .p-title {
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    /* ==========================================================
       RESPONSIVE MOBILE VIEW OPTIMIZATIONS (Smartphones / iPhone)
       ========================================================== */
    @media (max-width: 600px) {
      .container {
        padding: 10px 10px;
      }
      header {
        padding: max(8px, env(safe-area-inset-top, 8px)) 12px 8px 12px;
      }
      .brand-icon { font-size: 22px; }
      .brand h1 { font-size: 15px; }
      .brand p { font-size: 10px; }
      .btn-actions span { display: none; }
      .cloud-pill { padding: 3px 7px; font-size: 10px; }

      /* Compact 2x2 Metrics Grid on mobile phones */
      .metrics-grid {
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 10px 0 12px 0;
      }
      .metric-card {
        padding: 8px 10px;
      }
      .metric-label { font-size: 9.5px; }
      .metric-val { font-size: 20px; }
      .metric-sub { font-size: 10px; }

      /* Filters on mobile */
      .filters-section {
        padding: 10px;
        gap: 8px;
      }
      .filter-selects {
        grid-template-columns: 1fr;
        gap: 6px;
      }
      .select-filter {
        padding: 7px 8px;
        font-size: 12px;
      }

      /* Job Card Actions on Mobile: 2 full-width touch buttons side-by-side */
      .job-actions {
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
      }
      .action-group {
        display: flex;
        width: 100%;
        gap: 8px;
      }
      .btn-applied, .btn-apply-link {
        flex: 1;
        justify-content: center;
        text-align: center;
        padding: 9px 8px;
        font-size: 12.5px;
      }
      .job-date {
        text-align: center;
        font-size: 10.5px;
      }

      /* Sources Grid on Mobile */
      .sources-grid {
        grid-template-columns: 1fr;
      }

      /* Digest Iframe height */
      .digest-frame {
        height: 600px;
      }
    }
  </style>
</head>
<body>

  <!-- Top Sticky Navigation Header -->
  <header>
    <div class="header-content">
      <div class="brand">
        <span class="brand-icon">🎯</span>
        <div class="brand-text">
          <h1>Shubham's JobHunt</h1>
          <p>Autonomous AI Career Engine · Computer Engineering</p>
        </div>
      </div>
      <div class="header-actions">
        <div class="cloud-pill" title="Automations: 9:00 AM IST & Every 4h">
          <span class="dot"></span> Cloud Active
        </div>
        <a href="https://github.com/shubhaammm08/Job-Hunt/actions" target="_blank" class="btn-actions" title="Open GitHub Actions Runs">
          <span>⚡ Actions</span>
        </a>
      </div>
    </div>
  </header>

  <div class="container">

    <!-- Key Metrics Grid (2x2 on Mobile, 4x1 on Desktop) -->
    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label">Tracked Jobs</span>
        <span class="metric-val" id="metric-total">--</span>
        <span class="metric-sub">In seen.json</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Recommended</span>
        <span class="metric-val" id="metric-recommended" style="color: #3fb950;">--</span>
        <span class="metric-sub">Score ≥ 6.0</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Applied</span>
        <span class="metric-val" id="metric-applied" style="color: #58a6ff;">--</span>
        <span class="metric-sub" id="metric-applied-rate">0% applied</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Sources</span>
        <span class="metric-val" id="metric-sources">87</span>
        <span class="metric-sub">Connected</span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('tracker')">
        📊 Opportunities <span class="tab-badge" id="tab-count-jobs">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('digest')">
        📬 Daily Digest
      </button>
      <button class="tab-btn" onclick="switchTab('sources')">
        🛡️ Sources <span class="tab-badge">87</span>
      </button>
      <button class="tab-btn" onclick="switchTab('profile')">
        👤 Profile
      </button>
    </div>

    <!-- TAB 1: Opportunities Tracker -->
    <div id="tab-tracker" class="tab-panel active">
      
      <div class="filters-section">
        <!-- Search input -->
        <div class="search-row">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input type="text" id="search-input" placeholder="Search title, company, skill, city..." oninput="renderJobs()">
          </div>
        </div>

        <!-- 1-Touch Quick Filter Chips for Mobile Thumbs -->
        <div class="chips-scroll">
          <button class="filter-chip active" id="chip-all" onclick="setQuickChip('all')">All Jobs</button>
          <button class="filter-chip" id="chip-high" onclick="setQuickChip('high')">🔥 High Fit (8+)</button>
          <button class="filter-chip" id="chip-rec" onclick="setQuickChip('rec')">⭐ Recommended (6+)</button>
          <button class="filter-chip" id="chip-data" onclick="setQuickChip('data')">📊 Data Analyst</button>
          <button class="filter-chip" id="chip-ai" onclick="setQuickChip('ai')">🤖 AI / ML</button>
          <button class="filter-chip" id="chip-python" onclick="setQuickChip('python')">🐍 Python Dev</button>
          <button class="filter-chip" id="chip-unapplied" onclick="setQuickChip('unapplied')">⏳ Unapplied</button>
        </div>

        <!-- Dropdowns for fine tuning -->
        <div class="filter-selects">
          <select class="select-filter" id="filter-score" onchange="syncChipAndRender()">
            <option value="all">Score: Any</option>
            <option value="8">High Fit (8.0+)</option>
            <option value="6">Recommended (6.0+)</option>
            <option value="4">Plausible (4.0+)</option>
          </select>
          <select class="select-filter" id="filter-status" onchange="syncChipAndRender()">
            <option value="all">Status: All</option>
            <option value="unapplied">Not Applied</option>
            <option value="applied">Applied</option>
          </select>
          <select class="select-filter" id="filter-family" onchange="syncChipAndRender()">
            <option value="all">Family: All</option>
            <option value="DATA">Data Analyst / BI</option>
            <option value="AI_CORE">AI / ML Engineer</option>
            <option value="GENAI_AGENTIC">GenAI / Agentic</option>
            <option value="SOFTWARE">Software / Python</option>
          </select>
        </div>
      </div>

      <div class="results-count-bar">
        <span id="results-count">Showing 0 opportunities</span>
        <span style="font-size:11px;color:var(--text-muted);">Sorted by Compatibility Score</span>
      </div>

      <div class="job-list" id="job-list">
        <div style="text-align:center;padding:40px;color:var(--text-muted);">Loading opportunities...</div>
      </div>
    </div>

    <!-- TAB 2: Today's Job Digest Preview -->
    <div id="tab-digest" class="tab-panel">
      <div class="digest-container">
        <iframe class="digest-frame" id="digest-frame" src="gui/digest.html"></iframe>
      </div>
    </div>

    <!-- TAB 3: Source Health -->
    <div id="tab-sources" class="tab-panel">
      <div class="sources-grid" id="sources-grid">
        <div style="padding:20px;color:var(--text-muted);">Loading sources...</div>
      </div>
    </div>

    <!-- TAB 4: Profile & Preferences -->
    <div id="tab-profile" class="tab-panel">
      <div class="profile-card">
        <div class="profile-header">
          <div class="avatar">SK</div>
          <div>
            <h2 id="profile-name" style="font-size:18px;">Shubham Sunil Kadam</h2>
            <p style="color:var(--text-muted);font-size:13px;" id="profile-title">Data Analyst · Python, SQL & Junior AI Developer</p>
            <p style="color:var(--accent-blue);font-size:12px;margin-top:2px;" id="profile-email">ssk080204@gmail.com</p>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Target Career Tracks</div>
          <div class="job-tags" id="profile-target-roles"></div>
        </div>

        <div class="p-group">
          <div class="p-title">Core Technical Stack</div>
          <div class="job-tags" id="profile-skills"></div>
        </div>

        <div class="p-group">
          <div class="p-title">Target Locations</div>
          <div class="job-tags">
            <span class="tag">Mumbai</span>
            <span class="tag">Powai</span>
            <span class="tag">Pune</span>
            <span class="tag">Bangalore</span>
            <span class="tag">Hyderabad</span>
            <span class="tag">Delhi NCR</span>
            <span class="tag" style="background:#238636;color:#fff;font-weight:bold;">Remote (India & Global)</span>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Autonomous Cloud Schedules</div>
          <div style="font-size:12.5px;color:#c9d1d9;line-height:1.7;">
            ⏰ <strong>Daily JobHunter Digest:</strong> 9:00 AM IST (Daily)<br>
            📬 <strong>Inbox Executive Briefing:</strong> Every 4 Hours (02:17, 06:17, 10:17, 14:17, 18:17, 22:17 IST)<br>
            💰 <strong>Cost:</strong> ₹0/month on GitHub Actions Free Tier
          </div>
        </div>
      </div>
    </div>

  </div>

  <script>
    let appData = {
      jobs: [],
      stats: {},
      profile: {},
      source_health: [],
      digest_html: ""
    };

    let activeChip = 'all';

    function setQuickChip(chipType) {
      activeChip = chipType;
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      const activeEl = document.getElementById('chip-' + chipType);
      if (activeEl) activeEl.classList.add('active');

      const scoreSel = document.getElementById('filter-score');
      const statusSel = document.getElementById('filter-status');
      const familySel = document.getElementById('filter-family');

      // Reset dropdowns
      scoreSel.value = 'all';
      statusSel.value = 'all';
      familySel.value = 'all';

      if (chipType === 'high') scoreSel.value = '8';
      else if (chipType === 'rec') scoreSel.value = '6';
      else if (chipType === 'data') familySel.value = 'DATA';
      else if (chipType === 'ai') familySel.value = 'AI_CORE';
      else if (chipType === 'python') familySel.value = 'SOFTWARE';
      else if (chipType === 'unapplied') statusSel.value = 'unapplied';

      renderJobs();
    }

    function syncChipAndRender() {
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      renderJobs();
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');
      
      const targetPanel = document.getElementById('tab-' + tabId);
      if (targetPanel) targetPanel.classList.add('active');
    }

    async function loadData() {
      // 1. Initial pre-bundled payload if available
      if (window.INITIAL_DATA && window.INITIAL_DATA.jobs && window.INITIAL_DATA.jobs.length) {
        appData = window.INITIAL_DATA;
        renderAll();
      }
      // 2. Query local server API if running locally
      try {
        const res = await fetch('/api/data');
        if (res.ok) {
          appData = await res.json();
          renderAll();
        }
      } catch (err) {
        // Static mode or offline fallback
        if (!window.INITIAL_DATA) {
          loadStaticFallback();
        }
      }
    }

    function renderAll() {
      renderStats();
      renderJobs();
      renderSources();
      renderProfile();
      renderDigest();
    }

    function renderStats() {
      const stats = appData.stats || {};
      document.getElementById('metric-total').innerText = stats.total || 0;
      document.getElementById('metric-recommended').innerText = stats.recommended || 0;
      document.getElementById('metric-applied').innerText = stats.applied || 0;
      document.getElementById('metric-sources').innerText = stats.sources_count || 87;
      
      const rate = stats.total ? Math.round((stats.applied / stats.total) * 100) : 0;
      document.getElementById('metric-applied-rate').innerText = `${rate}% applied`;
      document.getElementById('tab-count-jobs').innerText = stats.total || 0;
    }

    function renderJobs() {
      const query = document.getElementById('search-input').value.toLowerCase().trim();
      const scoreFilter = document.getElementById('filter-score').value;
      const statusFilter = document.getElementById('filter-status').value;
      const familyFilter = document.getElementById('filter-family').value;

      const listContainer = document.getElementById('job-list');
      const filtered = (appData.jobs || []).filter(j => {
        if (query) {
          const hay = `${j.title || ''} ${j.company || ''} ${j.location || ''} ${(j.role_families || []).join(' ')} ${(j.matched_skills || []).join(' ')}`.toLowerCase();
          if (!hay.includes(query)) return false;
        }
        const score = parseFloat(j.score) || 0.0;
        if (scoreFilter === '8' && score < 8.0) return false;
        if (scoreFilter === '6' && score < 6.0) return false;
        if (scoreFilter === '4' && score < 4.0) return false;

        if (statusFilter === 'applied' && !j.applied) return false;
        if (statusFilter === 'unapplied' && j.applied) return false;

        if (familyFilter !== 'all') {
          const families = j.role_families || [];
          if (!families.includes(familyFilter)) return false;
        }
        return true;
      });

      document.getElementById('results-count').innerText = `Showing ${filtered.length} of ${appData.jobs.length} opportunities`;

      if (!filtered.length) {
        listContainer.innerHTML = `<div style="text-align:center;padding:50px 20px;color:var(--text-muted);background:var(--card-bg);border:1px dashed var(--card-border);border-radius:12px;">
          <div style="font-size:28px;margin-bottom:8px;">🔍</div>
          <div style="font-weight:600;color:var(--text-main);">No matching opportunities found</div>
          <div style="font-size:12px;margin-top:4px;">Try clearing your filters or searching for another keyword.</div>
        </div>`;
        return;
      }

      listContainer.innerHTML = filtered.map(j => {
        const score = parseFloat(j.score) || 0.0;
        const scoreClass = score >= 8.0 ? 'score-high' : (score >= 6.0 ? 'score-mid' : 'score-low');
        const appliedClass = j.applied ? 'is-applied' : '';
        const btnAppliedText = j.applied ? '✓ Applied' : 'Mark Applied';
        const btnAppliedClass = j.applied ? 'btn-applied active' : 'btn-applied';
        const src = j.canonical_source || j.source || j.ats || 'Direct';

        const familiesHtml = (j.role_families || []).slice(0, 2).map(f => `<span class="tag tag-family">${escapeHtml(f)}</span>`).join('');
        const skillsHtml = (j.matched_skills || []).slice(0, 3).map(s => `<span class="tag">${escapeHtml(s)}</span>`).join('');
        const sourcesNote = (j.sources && j.sources.length > 1) ? ` · Found on: ${j.sources.join(', ')}` : '';

        return `
          <div class="job-card ${appliedClass}" id="card-${j.job_id}">
            <div class="job-header">
              <div class="job-title-area">
                <div class="job-title">${escapeHtml(j.title || 'Untitled')}</div>
                <div class="job-meta-line">
                  <span class="job-company">${escapeHtml(j.company || 'Unknown')}</span>
                  <span class="job-location">📍 ${escapeHtml(j.location || 'Not Specified')}</span>
                </div>
              </div>
              <span class="score-badge ${scoreClass}">${score.toFixed(1)} Match</span>
            </div>

            <div class="job-tags">
              <span class="tag tag-source">⚡ ${escapeHtml(src)}</span>
              ${familiesHtml}
              ${skillsHtml}
            </div>

            ${j.reason ? `<div class="job-reason">💡 <strong>AI Fit:</strong> ${escapeHtml(j.reason)}</div>` : ''}

            <div class="job-actions">
              <span class="job-date">Seen: ${j.first_seen ? j.first_seen.split('T')[0] : 'Today'}${escapeHtml(sourcesNote)}</span>
              <div class="action-group">
                <button class="${btnAppliedClass}" onclick="toggleApplied('${j.job_id}')">${btnAppliedText}</button>
                <a href="${j.url || '#'}" target="_blank" rel="noopener noreferrer" class="btn-apply-link">Apply →</a>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    async function toggleApplied(jobId) {
      const job = (appData.jobs || []).find(j => j.job_id === jobId);
      if (!job) return;
      
      job.applied = !job.applied;
      renderStats();
      renderJobs();

      // If running with local python server
      try {
        await fetch('/api/toggle-applied', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId })
        });
      } catch (err) {
        // In static GitHub Pages mode, persist in localStorage so user's applied status stays saved!
        try {
          const appliedIds = JSON.parse(localStorage.getItem('jobhunt_applied') || '[]');
          if (job.applied && !appliedIds.includes(jobId)) appliedIds.push(jobId);
          else if (!job.applied) {
            const idx = appliedIds.indexOf(jobId);
            if (idx > -1) appliedIds.splice(idx, 1);
          }
          localStorage.setItem('jobhunt_applied', JSON.stringify(appliedIds));
        } catch (e) {}
      }
    }

    function renderSources() {
      const container = document.getElementById('sources-grid');
      const sources = appData.source_health || [];
      if (!sources.length) {
        container.innerHTML = '<div style="padding:20px;color:var(--text-muted);">87 Source Adapters Configured (Greenhouse, Ashby, Lever, Remotive, etc.)</div>';
        return;
      }
      container.innerHTML = sources.map(s => {
        const isHealthy = s.status === 'HEALTHY';
        const dotClass = isHealthy ? 'status-healthy' : 'status-config';
        return `
          <div class="source-card">
            <div class="source-info">
              <h4>${escapeHtml(s.source || '')}</h4>
              <span>${escapeHtml(s.category || '')} · Tier ${s.tier || 1}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-size:11px;color:var(--text-muted);">${s.status}</span>
              <span class="status-dot ${dotClass}"></span>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderProfile() {
      const p = appData.profile || {};
      if (p.name) document.getElementById('profile-name').innerText = p.name;
      if (p.current_title) document.getElementById('profile-title').innerText = p.current_title;
      
      const skillsContainer = document.getElementById('profile-skills');
      if (skillsContainer && p.core_skills) {
        skillsContainer.innerHTML = p.core_skills.map(s => `<span class="tag" style="background:#1f242d;color:#79c0ff;">${escapeHtml(s)}</span>`).join('');
      }

      const rolesContainer = document.getElementById('profile-target-roles');
      if (rolesContainer && p.target_titles) {
        rolesContainer.innerHTML = p.target_titles.map(t => `<span class="tag tag-family">${escapeHtml(t)}</span>`).join('');
      }
    }

    function renderDigest() {
      const iframe = document.getElementById('digest-frame');
      if (appData.digest_html && iframe) {
        iframe.srcdoc = appData.digest_html;
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function loadStaticFallback() {
      appData = {
        stats: { total: 48, applied: 0, recommended: 48, sources_count: 87 },
        profile: {
          name: "Shubham Sunil Kadam",
          current_title: "Data Analyst · Python, SQL & Junior AI Developer",
          core_skills: ["Python", "SQL", "Power BI", "Tableau", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning", "FastAPI", "PostgreSQL", "Docker", "Git"],
          target_titles: ["Data Analyst", "Junior AI Developer", "Python Developer", "Business Intelligence Analyst", "Analytics Engineer"]
        },
        source_health: [
          { source: "Greenhouse", category: "direct_ats", tier: 1, status: "HEALTHY" },
          { source: "Ashby", category: "direct_ats", tier: 1, status: "HEALTHY" },
          { source: "Lever", category: "direct_ats", tier: 1, status: "HEALTHY" },
          { source: "Remotive", category: "remote", tier: 3, status: "HEALTHY" },
          { source: "Remote OK", category: "remote", tier: 3, status: "HEALTHY" },
          { source: "Hacker News", category: "startup", tier: 3, status: "HEALTHY" }
        ],
        jobs: []
      };
      renderAll();
    }

    window.addEventListener('DOMContentLoaded', loadData);
  </script>
</body>
</html>
"""

def main():
    root = r"C:\Users\admin\Desktop\Hunt\PWP_jobhunt"
    gui_index = os.path.join(root, "gui", "index.html")
    with open(gui_index, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print("Updated gui/index.html with mobile-optimized responsive template.")

    # Now bundle live data into root index.html
    seen_path = os.path.join(root, "seen.json")
    seen_data = {}
    if os.path.exists(seen_path):
        with open(seen_path, "r", encoding="utf-8") as f:
            seen_data = json.load(f)

    profile_path = os.path.join(root, "profile.json")
    if not os.path.exists(profile_path):
        profile_path = os.path.join(root, "profile.example.json")
    with open(profile_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    health_path = os.path.join(root, "out", "source_health.json")
    health_data = []
    if os.path.exists(health_path):
        with open(health_path, "r", encoding="utf-8") as f:
            health_data = json.load(f)

    digest_path = os.path.join(root, "out", "digest.html")
    digest_html = ""
    if os.path.exists(digest_path):
        with open(digest_path, "r", encoding="utf-8") as f:
            digest_html = f.read()

    jobs_list = [{"job_id": k, **v} for k, v in seen_data.items() if isinstance(v, dict)]
    jobs_list.sort(key=lambda j: (j.get("score") or 0.0, j.get("first_seen") or ""), reverse=True)

    payload = {
        "jobs": jobs_list,
        "stats": {
            "total": len(jobs_list),
            "applied": sum(1 for j in jobs_list if j.get("applied")),
            "emailed": sum(1 for j in jobs_list if j.get("emailed")),
            "recommended": sum(1 for j in jobs_list if (j.get("score") or 0.0) >= 6.0),
            "sources_count": len(health_data) or 87
        },
        "profile": profile_data,
        "source_health": health_data,
        "digest_html": digest_html
    }

    injected_data = f"<script>window.INITIAL_DATA = {json.dumps(payload, ensure_ascii=False)};</script>\n</head>"
    root_html_content = HTML_TEMPLATE.replace("</head>", injected_data, 1)

    root_index = os.path.join(root, "index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(root_html_content)
    print(f"Updated root index.html with {len(jobs_list)} jobs and mobile enhancements.")

if __name__ == "__main__":
    main()
