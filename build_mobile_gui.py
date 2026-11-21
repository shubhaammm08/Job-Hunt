import os
import json
import re
import shutil

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="color-scheme" content="dark">
  <meta name="theme-color" content="#0d1117">
  <title>Shubham's JobHunt — Executive Dashboard</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%2358a6ff%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><circle cx=%2212%22 cy=%2212%22 r=%2210%22/><circle cx=%2212%22 cy=%2212%22 r=%226%22/><circle cx=%2212%22 cy=%2212%22 r=%222%22/></svg>">
  <style>
    :root {
      color-scheme: dark;
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

    /* SVG Icon Helpers */
    .icon {
      width: 14px;
      height: 14px;
      vertical-align: -2px;
      display: inline-block;
      flex-shrink: 0;
    }
    .icon-sm { width: 12px; height: 12px; vertical-align: -1px; }
    .icon-md { width: 16px; height: 16px; vertical-align: -3px; }
    .icon-lg { width: 24px; height: 24px; }

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
      display: flex;
      align-items: center;
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
      background: rgba(56, 139, 253, 0.15);
      border: 1px solid rgba(56, 139, 253, 0.4);
      color: var(--accent-blue);
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 999px;
      display: flex;
      align-items: center;
      gap: 5px;
      font-weight: 600;
      white-space: nowrap;
    }
    .cloud-pill .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #3fb950;
      box-shadow: 0 0 6px #3fb950;
    }
    .btn-actions {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      font-size: 11.5px;
      padding: 5px 10px;
      border-radius: 6px;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
      transition: background 0.15s;
    }
    .btn-actions:hover {
      background: #30363d;
    }

    /* Key Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin: 16px 0 20px 0;
    }
    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
    }
    .metric-card.clickable {
      cursor: pointer;
      transition: border-color 0.15s, transform 0.1s, box-shadow 0.15s;
    }
    .metric-card.clickable:hover {
      border-color: var(--accent-blue);
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    }
    .metric-card.clickable:active {
      transform: scale(0.985);
    }
    .btn-applied-hub-pill {
      font-size: 10px;
      font-weight: 700;
      color: var(--accent-blue);
      background: rgba(88, 166, 255, 0.15);
      border: 1px solid rgba(88, 166, 255, 0.35);
      padding: 2px 7px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-applied-hub-pill:hover {
      background: rgba(88, 166, 255, 0.3);
      border-color: var(--accent-blue);
    }
    .btn-applied-export {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      font-size: 12px;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      transition: all 0.15s;
      text-decoration: none;
    }
    .btn-applied-export:hover {
      border-color: var(--accent-blue);
      color: var(--accent-blue);
    }
    .metric-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .metric-val {
      font-size: 26px;
      font-weight: 800;
      color: var(--text-main);
      margin: 3px 0 1px 0;
      line-height: 1.1;
    }
    .metric-sub {
      font-size: 11px;
      color: var(--text-muted);
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
    .tab-panel.active { display: block; }

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

    /* Search Box */
    .search-row {
      display: flex;
      gap: 8px;
      width: 100%;
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
      padding: 9px 12px 9px 34px;
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
      display: flex;
      align-items: center;
    }

    /* Quick Filter Chips (1-touch on Mobile) */
    .chips-scroll {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
      padding: 4px 2px 8px 2px;
    }
    .chips-scroll::-webkit-scrollbar { display: none; }
    .filter-chip {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 600;
      padding: 9px 15px;
      min-height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      border-radius: 999px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      touch-action: manipulation;
      user-select: none;
      -webkit-user-select: none;
    }
    .filter-chip:hover { color: var(--text-main); }
    .filter-chip.active {
      background: rgba(88, 166, 255, 0.2);
      border-color: var(--accent-blue);
      color: #fff;
      box-shadow: 0 0 0 1px var(--accent-blue);
    }

    /* Detailed Dropdown Filters */
    .filter-selects {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }
    select {
      color-scheme: dark;
      background-color: #0d1117;
      color: var(--text-main);
    }
    select, .select-filter {
      color-scheme: dark;
      background-color: #0d1117;
      color: var(--text-main);
    }
    select option, select optgroup, .select-filter option {
      color-scheme: dark;
      background-color: #161b22;
      color: #e6edf3;
    }
    .select-filter {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 9px 12px;
      min-height: 42px;
      border-radius: 7px;
      font-size: 13px;
      outline: none;
      cursor: pointer;
      color-scheme: dark;
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
      transition: border-color 0.15s, transform 0.1s, box-shadow 0.15s;
      position: relative;
      cursor: pointer;
    }
    .job-card:hover {
      border-color: var(--accent-blue);
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
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
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .score-badge {
      font-size: 11.5px;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 6px;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .score-high {
      background: rgba(46, 160, 67, 0.2);
      border: 1px solid rgba(46, 160, 67, 0.4);
      color: #3fb950;
    }
    .score-mid {
      background: rgba(210, 153, 34, 0.2);
      border: 1px solid rgba(210, 153, 34, 0.4);
      color: #d29922;
    }
    .score-low {
      background: rgba(139, 148, 158, 0.15);
      border: 1px solid rgba(139, 148, 158, 0.3);
      color: var(--text-muted);
    }

    /* Tags & Reasoning */
    .job-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
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
      display: inline-flex;
      align-items: center;
      gap: 4px;
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
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .tag-src-greenhouse {
      background: rgba(46, 160, 67, 0.16);
      border: 1px solid rgba(46, 160, 67, 0.45);
      color: #3fb950;
    }
    .tag-src-ashby {
      background: rgba(188, 140, 255, 0.16);
      border: 1px solid rgba(188, 140, 255, 0.45);
      color: #d2a8ff;
    }
    .tag-src-lever {
      background: rgba(56, 189, 248, 0.16);
      border: 1px solid rgba(56, 189, 248, 0.45);
      color: #38bdf8;
    }
    .tag-src-linkedin {
      background: rgba(10, 102, 194, 0.22);
      border: 1px solid rgba(10, 102, 194, 0.5);
      color: #70b5f9;
    }
    .tag-src-naukri {
      background: rgba(69, 123, 247, 0.2);
      border: 1px solid rgba(69, 123, 247, 0.45);
      color: #60a5fa;
    }
    .tag-src-remoteok {
      background: rgba(248, 81, 73, 0.18);
      border: 1px solid rgba(248, 81, 73, 0.45);
      color: #ff7b72;
    }
    .tag-src-remotive {
      background: rgba(236, 72, 153, 0.18);
      border: 1px solid rgba(236, 72, 153, 0.45);
      color: #f472b6;
    }
    .tag-src-nodesk {
      background: rgba(139, 92, 246, 0.18);
      border: 1px solid rgba(139, 92, 246, 0.45);
      color: #a78bfa;
    }
    .tag-src-workingnomads {
      background: rgba(20, 184, 166, 0.18);
      border: 1px solid rgba(20, 184, 166, 0.45);
      color: #2dd4bf;
    }
    .tag-src-hackernews {
      background: rgba(255, 102, 0, 0.18);
      border: 1px solid rgba(255, 102, 0, 0.45);
      color: #ff944d;
    }
    .tag-src-smartrecruiters {
      background: rgba(99, 102, 241, 0.18);
      border: 1px solid rgba(99, 102, 241, 0.45);
      color: #818cf8;
    }
    .tag-src-workable {
      background: rgba(245, 158, 11, 0.18);
      border: 1px solid rgba(245, 158, 11, 0.45);
      color: #fbbf24;
    }
    .tag-src-indeed {
      background: rgba(37, 99, 235, 0.18);
      border: 1px solid rgba(37, 99, 235, 0.45);
      color: #93c5fd;
    }
    .tag-src-direct_ats {
      background: rgba(59, 130, 246, 0.18);
      border: 1px solid rgba(59, 130, 246, 0.45);
      color: #60a5fa;
    }
    .tag-src-other {
      background: rgba(139, 148, 158, 0.15);
      border: 1px solid rgba(139, 148, 158, 0.35);
      color: #8b949e;
    }

    /* Workplace Tag Styles */
    .tag-workplace {
      font-weight: 600;
    }
    .tag-wp-remote {
      background: rgba(46, 160, 67, 0.15);
      border: 1px solid rgba(46, 160, 67, 0.4);
      color: #3fb950;
    }
    .tag-wp-hybrid {
      background: rgba(188, 140, 255, 0.15);
      border: 1px solid rgba(188, 140, 255, 0.4);
      color: #d2a8ff;
    }
    .tag-wp-onsite {
      background: rgba(88, 166, 255, 0.15);
      border: 1px solid rgba(88, 166, 255, 0.4);
      color: #79c0ff;
    }
    .tag-wp-other {
      background: rgba(139, 148, 158, 0.15);
      border: 1px solid rgba(139, 148, 158, 0.4);
      color: #8b949e;
    }
    .tag-applied {
      background: rgba(46, 160, 67, 0.18);
      border: 1px solid rgba(46, 160, 67, 0.5);
      color: #3fb950;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 3px;
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
      display: flex;
      align-items: flex-start;
      gap: 6px;
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
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .btn-applied.active {
      background: rgba(46, 160, 67, 0.22);
      border-color: #3fb950;
      color: #3fb950;
      font-weight: 700;
    }
    .btn-kit {
      background: rgba(188, 140, 255, 0.12);
      border: 1px solid rgba(188, 140, 255, 0.35);
      color: #d2a8ff;
      font-size: 12.5px;
      padding: 7px 11px;
      border-radius: 7px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s;
      touch-action: manipulation;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }
    .btn-kit:hover {
      background: rgba(188, 140, 255, 0.22);
      border-color: #d2a8ff;
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

    /* Modal Backdrop & Drawer Styles */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.78);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
    }
    .modal-backdrop.open {
      opacity: 1;
      pointer-events: auto;
    }
    .modal-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      max-width: 680px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 16px 40px rgba(0,0,0,0.6);
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      position: relative;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
    }
    .modal-close-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
    }
    .modal-close-btn:hover { color: var(--text-main); background: #21262d; }
    .kit-section {
      background: rgba(0,0,0,0.28);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 10px;
      padding: 14px;
    }
    .kit-sec-title {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .btn-copy-chip {
      background: rgba(88, 166, 255, 0.15);
      border: 1px solid rgba(88, 166, 255, 0.35);
      color: var(--accent-blue);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 5px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s;
    }
    .btn-copy-chip:hover { background: rgba(88, 166, 255, 0.28); }
    .btn-copy-chip.copied {
      background: rgba(46, 160, 67, 0.25);
      border-color: #3fb950;
      color: #3fb950;
    }
    .kit-textarea {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #c9d1d9;
      font-size: 12.5px;
      line-height: 1.5;
      padding: 10px;
      resize: vertical;
      font-family: var(--font);
      box-sizing: border-box;
    }
    .screening-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    @media (max-width: 600px) {
      .screening-grid { grid-template-columns: 1fr; }
    }
    .screening-item {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      font-size: 12px;
    }
    .screening-val {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text-main);
    }
    .bookmarklet-box {
      background: rgba(35, 134, 54, 0.12);
      border: 1px solid rgba(46, 160, 67, 0.35);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .bookmarklet-link {
      background: var(--accent-green);
      color: #fff;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      width: fit-content;
      cursor: grab;
      border: 1px solid rgba(255,255,255,0.15);
    }
    .bookmarklet-link:hover { background: var(--green-light); }
    .toast-msg {
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      background: #1f6feb;
      color: #fff;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      z-index: 2000;
      display: flex;
      align-items: center;
      gap: 8px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
      max-width: 90vw;
      text-align: center;
    }
    .toast-msg.show {
      opacity: 1;
      transform: translateX(-50%) translateY(-6px);
      pointer-events: auto;
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
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 10px;
    }
    .source-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .source-info h4 {
      font-size: 13.5px;
      margin-bottom: 2px;
    }
    .source-info span {
      font-size: 11px;
      color: var(--text-muted);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .status-healthy { background: #3fb950; box-shadow: 0 0 6px rgba(63, 185, 80, 0.4); }
    .status-config { background: #d29922; }

    
    /* Source Hub Styling */
    .source-banner {
      background: rgba(56, 139, 253, 0.08);
      border: 1px solid rgba(88, 166, 255, 0.2);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 14px;
      font-size: 12.5px;
      line-height: 1.5;
    }
    .source-banner-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13.5px;
      color: var(--text-main);
      margin-bottom: 6px;
    }
    .source-banner p {
      color: var(--text-muted);
      margin: 0;
    }
    .source-desc {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
      line-height: 1.35;
    }
    .badge-pill {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .badge-healthy {
      background: rgba(46, 160, 67, 0.18);
      color: #3fb950;
      border: 1px solid rgba(46, 160, 67, 0.4);
    }
    .badge-config {
      background: rgba(210, 153, 34, 0.15);
      color: #e3b341;
      border: 1px solid rgba(210, 153, 34, 0.35);
    }

    /* Profile Panel */
    .profile-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
    }
    .profile-header {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
    }
    .avatar {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: linear-gradient(135deg, #1f6feb, #238636);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      flex-shrink: 0;
    }
    .p-group {
      margin-bottom: 18px;
    }
    .p-title {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }

    /* Mobile Responsive Breakpoints */
    @media (max-width: 600px) {
      .container { padding: 10px; }
      header { padding: max(8px, env(safe-area-inset-top, 8px)) 12px 8px 12px; }
      .brand h1 { font-size: 15px; }
      .brand p { font-size: 10px; }
      .header-actions .btn-actions span { display: none; }
      #btn-linkedin-scrape span { display: inline !important; }
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
        gap: 8px;
      }
      .select-filter {
        padding: 10px 12px;
        font-size: 14px;
        min-height: 44px;
      }
      .filter-chip {
        padding: 10px 14px;
        font-size: 13px;
        min-height: 44px;
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
        padding: 10px 14px;
        font-size: 13px;
        min-height: 44px;
        display: inline-flex;
        align-items: center;
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
        <span class="brand-icon">
          <svg class="icon icon-lg" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
          </svg>
        </span>
        <div class="brand-text">
          <h1>Shubham's JobHunt</h1>
          <p>Opportunity Pipeline &amp; Application Tracker · Computer Engineering</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn-actions" onclick="openWhatsAppGuide()" title="Phone Alerts (Telegram &amp; WhatsApp)" style="cursor:pointer;background:rgba(56,189,248,0.12);border-color:rgba(56,189,248,0.35);color:#38bdf8;">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
          </svg>
          <span>Phone Alerts</span>
        </button>
        <button class="btn-actions" onclick="openBookmarkletGuide()" title="1-Click ATS Auto-Fill Tool" style="cursor:pointer;background:rgba(188,140,255,0.12);border-color:rgba(188,140,255,0.35);color:#d2a8ff;">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <span>Auto-Fill Tool</span>
        </button>
        <div class="cloud-pill" title="Scheduled Runs: 09:00 IST &amp; Every 4h">
          <span class="dot"></span> Pipeline Active
        </div>
        <a href="https://github.com/shubhaammm08/Job-Hunt/actions" target="_blank" class="btn-actions" title="Open GitHub Actions Runs">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <span>Actions</span>
        </a>
      </div>
    </div>
  </header>

  <div class="container">

    <!-- Key Metrics Grid (2x2 on Mobile, 4x1 on Desktop) -->
    <div class="metrics-grid">
      <div class="metric-card clickable" onclick="setQuickChip('all')" title="Filter: All Tracked Jobs" role="button" tabindex="0">
        <span class="metric-label">Tracked Jobs</span>
        <span class="metric-val" id="metric-total">--</span>
        <span class="metric-sub">In seen.json</span>
      </div>
      <div class="metric-card clickable" onclick="setQuickChip('rec')" title="Filter: Recommended (Score ≥ 6.0)" role="button" tabindex="0">
        <span class="metric-label">Recommended</span>
        <span class="metric-val" id="metric-recommended" style="color: #3fb950;">--</span>
        <span class="metric-sub">Score ≥ 6.0</span>
      </div>
      <div class="metric-card clickable" id="metric-card-applied" onclick="setQuickChip('applied')" title="Filter: View Applied Jobs (or click Hub to manage)" role="button" tabindex="0">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="metric-label">Applied</span>
          <button class="btn-applied-hub-pill" onclick="event.stopPropagation(); openAppliedTrackerModal();" title="Open Applied Jobs Hub">Hub ↗</button>
        </div>
        <span class="metric-val" id="metric-applied" style="color: #58a6ff;">--</span>
        <span class="metric-sub" id="metric-applied-rate">0% applied</span>
      </div>
      <div class="metric-card clickable" onclick="switchTab('sources')" title="View Connected Sources" role="button" tabindex="0">
        <span class="metric-label">Sources</span>
        <span class="metric-val" id="metric-sources">87</span>
        <span class="metric-sub">Connected</span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('tracker')">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
        </svg> Opportunities <span class="tab-badge" id="tab-count-jobs">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('digest')">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
        </svg> Daily Digest
      </button>
      <button class="tab-btn" onclick="switchTab('sources')">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg> Sources <span class="tab-badge">87</span>
      </button>
      <button class="tab-btn" onclick="switchTab('profile')">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
        </svg> Profile
      </button>
    </div>

    <!-- TAB 1: Opportunities Tracker -->
    <div id="tab-tracker" class="tab-panel active">
      
      <div class="filters-section">
        <!-- Search input -->
        <div class="search-row">
          <div class="search-box">
            <span class="search-icon">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </span>
            <input type="text" id="search-input" placeholder="Search title, company, skill, city..." oninput="renderJobs()">
          </div>
          <button class="btn-applied-export" onclick="openAppliedTrackerModal()" title="View and manage all applied jobs" style="height:44px;padding:0 14px;flex-shrink:0;">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>Applied Hub</span>
          </button>
        </div>

        <!-- 1-Touch Quick Filter Chips for Mobile Thumbs -->
        <div class="chips-scroll" role="region" aria-label="Quick filters">
          <button class="filter-chip active" id="chip-all" onclick="setQuickChip('all')">All Jobs</button>
          <button class="filter-chip" id="chip-applied" onclick="setQuickChip('applied')">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg> Applied (<span id="chip-count-applied">0</span>)
          </button>
          <button class="filter-chip" id="chip-high" onclick="setQuickChip('high')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg> High Fit (8+)
          </button>
          <button class="filter-chip" id="chip-rec" onclick="setQuickChip('rec')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> Recommended (6+)
          </button>
          <button class="filter-chip" id="chip-unapplied" onclick="setQuickChip('unapplied')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> Unapplied
          </button>

          <!-- Workplace Types -->
          <button class="filter-chip" id="chip-remote" onclick="setQuickChip('remote')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg> Remote
          </button>
          <button class="filter-chip" id="chip-hybrid" onclick="setQuickChip('hybrid')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg> Hybrid
          </button>
          <button class="filter-chip" id="chip-onsite" onclick="setQuickChip('onsite')">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg> Onsite
          </button>

          <!-- ATS / Platform Sources -->
          <button class="filter-chip" id="chip-greenhouse" onclick="setQuickChip('greenhouse')">Greenhouse</button>
          <button class="filter-chip" id="chip-ashby" onclick="setQuickChip('ashby')">Ashby</button>
          <button class="filter-chip" id="chip-lever" onclick="setQuickChip('lever')">Lever</button>
          <button class="filter-chip" id="chip-linkedin" onclick="setQuickChip('linkedin')">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
              <rect x="2" y="9" width="4" height="12"/>
              <circle cx="4" cy="4" r="2"/>
            </svg> LinkedIn
          </button>
          <button class="filter-chip" id="chip-remotive" onclick="setQuickChip('remotive')">Remotive</button>
          <button class="filter-chip" id="chip-hackernews" onclick="setQuickChip('hackernews')">Hacker News</button>
          <button class="filter-chip" id="chip-other-plat" onclick="setQuickChip('other_plat')">Other Sources</button>

          <!-- Career Tracks -->
          <button class="filter-chip" id="chip-data" onclick="setQuickChip('data')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg> Data Analyst
          </button>
          <button class="filter-chip" id="chip-ai" onclick="setQuickChip('ai')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg> AI / ML
          </button>
          <button class="filter-chip" id="chip-python" onclick="setQuickChip('python')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg> Python Dev
          </button>
        </div>

        <!-- Detailed Dropdowns for Fine-Tuned Multi-Filtering -->
        <div class="filter-selects">
          <select class="select-filter" id="filter-score" onchange="syncChipAndRender()" aria-label="Filter by compatibility score">
            <option value="all">Score: Any</option>
            <option value="8">High Fit (8.0+)</option>
            <option value="6">Recommended (6.0+)</option>
            <option value="4">Plausible (4.0+)</option>
          </select>
          <select class="select-filter" id="filter-status" onchange="syncChipAndRender()" aria-label="Filter by application status">
            <option value="all">Status: All</option>
            <option value="unapplied">Not Applied</option>
            <option value="applied">Applied</option>
          </select>
          <select class="select-filter" id="filter-family" onchange="syncChipAndRender()" aria-label="Filter by role family">
            <option value="all">Family: All</option>
            <option value="DATA">Data Analyst / BI</option>
            <option value="AI_CORE">AI / ML Engineer</option>
            <option value="GENAI_AGENTIC">GenAI / Agentic</option>
            <option value="SOFTWARE">Software / Python</option>
          </select>
          <select class="select-filter" id="filter-workplace" onchange="syncChipAndRender()" aria-label="Filter by workplace type">
            <option value="all">Workplace: All</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
            <option value="other">Other / Unspecified</option>
          </select>
          <select class="select-filter" id="filter-platform" onchange="syncChipAndRender()" aria-label="Filter by platform source">
            <option value="all">Platform: All</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="ashby">Ashby</option>
            <option value="lever">Lever</option>
            <option value="remotive">Remotive</option>
            <option value="hackernews">Hacker News</option>
            <option value="remoteok">Remote OK</option>
            <option value="nodesk">NoDesk</option>
            <option value="workingnomads">Working Nomads</option>
            <option value="linkedin">LinkedIn</option>
            <option value="naukri">Naukri</option>
            <option value="indeed">Indeed</option>
            <option value="smartrecruiters">SmartRecruiters</option>
            <option value="workable">Workable</option>
            <option value="direct_ats">Direct ATS / Company</option>
            <option value="other">Other / Unspecified</option>
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
        <iframe class="digest-frame" id="digest-frame" src="digest.html"></iframe>
      </div>
    </div>

    <!-- TAB 3: Source Health & Architecture -->
    <div id="tab-sources" class="tab-panel">
      <div class="source-banner">
        <div class="source-banner-header">
          <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <strong>Cloud Ingestion Engine: 17 Active Live Feeds &amp; 35+ Company Boards</strong>
        </div>
        <p>
          The automated runner queries open, legal ATS APIs (Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Personio, Breezy, Remotive, Remote OK, Himalayas, Jobicy, Working Nomads, NoDesk, Hacker News) daily at 09:00 IST without credentials.
          Commercial portals (LinkedIn, Naukri, Indeed) and Enterprise ATS (Workday) block automated scraping via Cloudflare bot protection and require custom feed URLs or partner API keys.
        </p>
      </div>

      <!-- Sources Filter Pills -->
      <div class="chips-scroll" style="margin-bottom: 14px;">
        <button class="filter-chip active" id="source-chip-active" onclick="filterSources('active')">
          <span class="status-dot status-healthy" style="display:inline-block;margin-right:4px;"></span> Active &amp; Scanned (17)
        </button>
        <button class="filter-chip" id="source-chip-all" onclick="filterSources('all')">
          All Platforms (88)
        </button>
        <button class="filter-chip" id="source-chip-direct_ats" onclick="filterSources('direct_ats')">
          Direct ATS (30)
        </button>
        <button class="filter-chip" id="source-chip-remote" onclick="filterSources('remote')">
          Remote &amp; Startup (18)
        </button>
        <button class="filter-chip" id="source-chip-india_job_board" onclick="filterSources('india_job_board')">
          India &amp; Global Portals (23)
        </button>
        <button class="filter-chip" id="source-chip-fresher" onclick="filterSources('fresher')">
          Fresher &amp; AI (17)
        </button>
      </div>

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
            <p style="color:var(--text-muted);font-size:13px;" id="profile-title">AI &amp; Software Engineer</p>
            <p style="color:var(--accent-blue);font-size:12px;margin-top:2px;" id="profile-email">ssk080204@gmail.com · +918169832448</p>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Target Career Tracks</div>
          <div class="job-tags" id="profile-target-roles">
            <span class="tag tag-family">AI Engineer</span>
            <span class="tag tag-family">GenAI &amp; LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)</span>
            <span class="tag tag-family">API Development / Backend Engineer (FastAPI, Flask, REST APIs)</span>
            <span class="tag tag-family">Full-Stack Developer / Engineer (React, Node.js)</span>
            <span class="tag tag-family">Mobile Developer (Flutter)</span>
            <span class="tag tag-family">Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)</span>
            <span class="tag tag-family">Machine Learning &amp; Python Developer</span>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Core Technical Stack &amp; Skills</div>
          <div class="job-tags" id="profile-skills">
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">AI &amp; ML:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Machine Learning</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">GenAI</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">LLMs</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">NLP</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">LangChain</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Python</span>
            </div>
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">API &amp; Backend:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">FastAPI</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Flask</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">REST APIs</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Node.js</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Python</span>
            </div>
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">Full-Stack &amp; Frontend:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">React</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Node.js</span>
            </div>
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">Mobile:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Flutter</span>
            </div>
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">Automation &amp; DevOps:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">n8n</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Docker</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">CI/CD</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Automation</span>
            </div>
            <div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">Data &amp; BI:</strong></div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
              <span class="tag" style="background:#1f242d;color:#79c0ff;">SQL</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Power BI</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Pandas</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">NumPy</span>
              <span class="tag" style="background:#1f242d;color:#79c0ff;">Scikit-learn</span>
            </div>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Target Locations</div>
          <div class="job-tags">
            <span class="tag" style="background:#1f242d;color:#58a6ff;font-weight:600;">Mumbai Metropolitan Region</span>
            <span class="tag" style="background:#238636;color:#fff;font-weight:bold;">Remote</span>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Pipeline Automation Schedules</div>
          <div style="font-size:12.5px;color:#c9d1d9;line-height:1.8;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
              <span><strong>Daily Digest:</strong> 09:00 IST (Daily)</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              <span><strong>Notification Dispatch:</strong> Every 4 Hours (02:17, 06:17, 10:17, 14:17, 18:17, 22:17 IST)</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
              </svg>
              <span><strong>Infrastructure:</strong> GitHub Actions (Free Tier)</span>
            </div>
          </div>
        </div>

        <div class="p-group">
          <div class="p-title">Phone Alerts &amp; Notification Gateways (Free Tier)</div>
          <div style="font-size:12.5px;color:#c9d1d9;line-height:1.8;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>
              </svg>
              <span><strong>Telegram Bot:</strong> @ShubhamJobHunt_Bot (<span style="color:#2ea043;font-weight:700;">Active &amp; Connected</span>)</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
              </svg>
              <span><strong>WhatsApp Gateway:</strong> CallMeBot / Twilio (Ready)</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              <span><strong>Triggers:</strong> High-Fit Roles (Fit Score &ge; 8.0) + Daily 09:00 IST Morning Summary</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              <span><strong>Delivery:</strong> 1-Click Direct Apply Links + Tailored Pitch Note to Phone</span>
            </div>
            <button class="btn-copy-chip" onclick="openWhatsAppGuide()" style="padding:6px 14px;font-size:12px;cursor:pointer;">
              View Connected Phone Alert Details
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Modal 1: Auto-Fill Application Kit Modal -->
  <div class="modal-backdrop" id="modal-apply-kit" onclick="if(event.target===this)closeApplyKit()">
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="kit-modal-title">
      <div class="modal-header">
        <div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span class="tag tag-source">
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              1-Click Application Kit
            </span>
          </div>
          <h2 id="kit-modal-title" style="font-size:17px;font-weight:800;color:var(--text-main);">Role at Company</h2>
          <p id="kit-modal-meta" style="font-size:12px;color:var(--text-muted);margin-top:2px;">Location · Match Score</p>
        </div>
        <button class="modal-close-btn" onclick="closeApplyKit()" aria-label="Close modal">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Section A: 1-Click ATS AutoFill Bar -->
      <div class="bookmarklet-box">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
          <div>
            <div style="font-weight:700;font-size:13px;color:#3fb950;display:flex;align-items:center;gap:6px;">
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              Universal ATS 1-Click Form AutoFiller
            </div>
            <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">
              Drag the button to your browser bookmarks bar to autofill Greenhouse, Lever, Ashby &amp; Workable in 1 click!
            </div>
          </div>
          <button class="btn-copy-chip" onclick="copyBookmarkletCode(this)">Copy Script</button>
        </div>
      </div>

      <!-- Section B: Tailored Cover Letter -->
      <div class="kit-section">
        <div class="kit-sec-title">
          <span>Tailored Cover Letter (Pre-Drafted for this Company)</span>
          <button class="btn-copy-chip" id="btn-copy-cover" onclick="copyFieldValue(document.getElementById('kit-cover-note').value, this)">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy Letter
          </button>
        </div>
        <textarea id="kit-cover-note" class="kit-textarea" rows="6" readonly></textarea>
      </div>

      <!-- Section C: 2-Sentence Recruiter Hook -->
      <div class="kit-section">
        <div class="kit-sec-title">
          <span>2-Sentence Recruiter Hook (For InMail / Quick Pitch)</span>
          <button class="btn-copy-chip" id="btn-copy-pitch" onclick="copyFieldValue(document.getElementById('kit-pitch-hook').value, this)">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy Pitch
          </button>
        </div>
        <textarea id="kit-pitch-hook" class="kit-textarea" rows="3" readonly></textarea>
      </div>

      <!-- Section D: Standard ATS Screening Answers -->
      <div class="kit-section">
        <div class="kit-sec-title">Standard Screening Responses</div>
        <div class="screening-grid">
          <div class="screening-item">
            <span class="screening-val"><strong>Notice:</strong> Immediate (0-15d)</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('Immediate / 0-15 days', this)">Copy</button>
          </div>
          <div class="screening-item">
            <span class="screening-val"><strong>Work Auth:</strong> India (Citizen)</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('Authorized to work in India (Citizen) / Open to Remote', this)">Copy</button>
          </div>
          <div class="screening-item">
            <span class="screening-val"><strong>Location:</strong> Mumbai, India</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('Mumbai, Maharashtra, India', this)">Copy</button>
          </div>
          <div class="screening-item">
            <span class="screening-val"><strong>Sponsorship:</strong> Not Needed</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('No sponsorship required', this)">Copy</button>
          </div>
          <div class="screening-item">
            <span class="screening-val"><strong>LinkedIn:</strong> linkedin.com/in/...</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('https://www.linkedin.com/in/shubham-kadam', this)">Copy</button>
          </div>
          <div class="screening-item">
            <span class="screening-val"><strong>GitHub:</strong> github.com/shubhaammm08</span>
            <button class="btn-copy-chip" onclick="copyFieldValue('https://github.com/shubhaammm08', this)">Copy</button>
          </div>
        </div>
      </div>

      <!-- Footer Buttons -->
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding-top:12px;border-top:1px solid var(--card-border);">
        <div style="display:flex;align-items:center;gap:8px;">
          <label for="kit-browser-select" style="font-size:12px;font-weight:600;color:var(--text-muted);display:flex;align-items:center;gap:4px;">
            Target Browser:
          </label>
          <select id="kit-browser-select" class="select-filter" style="padding:6px 12px;font-size:12.5px;border-radius:6px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);color-scheme:dark;min-height:36px;cursor:pointer;" onchange="savePreferredBrowser(this.value)">
            <option value="edge">Microsoft Edge (Separate App)</option>
            <option value="brave">Brave Browser (Local)</option>
            <option value="window">Side-by-Side Companion Window</option>
            <option value="tab">Same Browser (New Tab)</option>
          </select>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button class="btn-applied" onclick="closeApplyKit()">Close Kit</button>
          <button class="btn-apply-link" id="kit-launch-btn" style="padding:10px 18px;font-size:13.5px;cursor:pointer;">
            Launch Job &amp; Keep Kit Open <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal 2: 1-Click ATS AutoFill Bookmarklet Guide Modal -->
  <div class="modal-backdrop" id="modal-bookmarklet-guide" onclick="if(event.target===this)closeBookmarkletGuide()">
    <div class="modal-card" style="max-width:680px;" role="dialog" aria-modal="true" aria-labelledby="guide-modal-title">
      <div class="modal-header">
        <h2 id="guide-modal-title" style="font-size:17px;font-weight:800;color:var(--text-main);">Universal ATS 1-Click Form AutoFiller</h2>
        <button class="modal-close-btn" onclick="closeBookmarkletGuide()" aria-label="Close modal">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div style="font-size:13px;color:#c9d1d9;line-height:1.6;display:flex;flex-direction:column;gap:14px;">
        <p>
          Apply to any job in <strong>under 5 seconds</strong>. This tool detects form fields on <strong>Greenhouse, Lever, Ashby, Workable, SmartRecruiters, and BambooHR</strong> and populates your name, email, phone, location, LinkedIn, GitHub, portfolio, and standard screening answers instantly.
        </p>

        <!-- Drag Link & Bookmarklet Box -->
        <div class="bookmarklet-box" style="align-items:center;text-align:center;padding:16px;">
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Drag this button directly to your browser's Bookmarks Bar:</div>
          <a class="bookmarklet-link" id="bookmarklet-drag-link" href="#" onclick="event.preventDefault();showToast('Drag this button to your Bookmarks Bar (or click Copy Script below).');">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            AutoFill JobHunt
          </a>
          <div style="margin-top:8px;">
            <button class="btn-copy-chip" onclick="copyBookmarkletCode(this)">
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              Copy Bookmarklet JavaScript
            </button>
          </div>
        </div>

        <!-- Inline Editable Candidate Profile Section -->
        <div class="autofill-profile-section" style="background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
            <div>
              <div style="font-weight:700;font-size:13.5px;color:var(--text-main);display:flex;align-items:center;gap:6px;">
                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                Applicant Profile &amp; AutoFill Fields
              </div>
              <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">
                Customize your details. Changes persist in local storage and dynamically update the bookmarklet.
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <button type="button" class="btn-copy-chip" id="btn-autofill-reset" onclick="resetAutofillProfile()" style="background:rgba(248,81,73,0.12);border-color:rgba(248,81,73,0.35);color:#f85149;" title="Reset all fields to candidate defaults">
                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                Reset to Defaults
              </button>
              <button type="button" class="btn-apply-link" id="btn-autofill-save" onclick="saveAutofillProfile()" style="padding:6px 14px;font-size:12px;cursor:pointer;">
                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                Save
              </button>
            </div>
          </div>

          <!-- 12 Input Fields in Responsive Grid -->
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));gap:10px;">
            <!-- First Name -->
            <div class="autofill-field-group">
              <label for="autofill-first-name" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">First Name</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-first-name" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="First Name">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-first-name', this)" title="Copy First Name" aria-label="Copy First Name">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Last Name -->
            <div class="autofill-field-group">
              <label for="autofill-last-name" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Last Name</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-last-name" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Last Name">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-last-name', this)" title="Copy Last Name" aria-label="Copy Last Name">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Full Name -->
            <div class="autofill-field-group">
              <label for="autofill-full-name" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Full Name</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-full-name" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Full Name">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-full-name', this)" title="Copy Full Name" aria-label="Copy Full Name">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Email -->
            <div class="autofill-field-group">
              <label for="autofill-email" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Email</label>
              <div style="display:flex;gap:6px;">
                <input type="email" id="autofill-email" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Email">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-email', this)" title="Copy Email" aria-label="Copy Email">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Phone -->
            <div class="autofill-field-group">
              <label for="autofill-phone" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Phone</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-phone" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Phone">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-phone', this)" title="Copy Phone" aria-label="Copy Phone">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Location -->
            <div class="autofill-field-group">
              <label for="autofill-location" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Location</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-location" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="City, State, Country">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-location', this)" title="Copy Location" aria-label="Copy Location">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- LinkedIn -->
            <div class="autofill-field-group">
              <label for="autofill-linkedin" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">LinkedIn</label>
              <div style="display:flex;gap:6px;">
                <input type="url" id="autofill-linkedin" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="LinkedIn Profile URL">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-linkedin', this)" title="Copy LinkedIn" aria-label="Copy LinkedIn">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- GitHub -->
            <div class="autofill-field-group">
              <label for="autofill-github" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">GitHub</label>
              <div style="display:flex;gap:6px;">
                <input type="url" id="autofill-github" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="GitHub Profile URL">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-github', this)" title="Copy GitHub" aria-label="Copy GitHub">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Portfolio URL -->
            <div class="autofill-field-group">
              <label for="autofill-portfolio" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Portfolio URL</label>
              <div style="display:flex;gap:6px;">
                <input type="url" id="autofill-portfolio" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Portfolio URL">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-portfolio', this)" title="Copy Portfolio" aria-label="Copy Portfolio">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Notice Period -->
            <div class="autofill-field-group">
              <label for="autofill-notice-period" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Notice Period</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-notice-period" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Notice Period">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-notice-period', this)" title="Copy Notice Period" aria-label="Copy Notice Period">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Work Auth -->
            <div class="autofill-field-group" style="grid-column: 1 / -1;">
              <label for="autofill-work-auth" style="font-size:11.5px;font-weight:600;color:var(--text-muted);margin-bottom:3px;display:block;">Work Auth</label>
              <div style="display:flex;gap:6px;">
                <input type="text" id="autofill-work-auth" class="select-filter" style="width:100%;min-height:34px;padding:6px 10px;font-size:12.5px;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;" placeholder="Work Authorization (e.g. Yes / Citizen)">
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-work-auth', this)" title="Copy Work Auth" aria-label="Copy Work Auth">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
            </div>

            <!-- Summary / Pitch -->
            <div class="autofill-field-group" style="grid-column: 1 / -1;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
                <label for="autofill-summary" style="font-size:11.5px;font-weight:600;color:var(--text-muted);display:block;">Summary / Pitch</label>
                <button type="button" class="btn-copy-chip" onclick="copyAutofillField('autofill-summary', this)" title="Copy Summary/Pitch" aria-label="Copy Summary/Pitch">
                  <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy
                </button>
              </div>
              <textarea id="autofill-summary" class="kit-textarea" rows="3" style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid var(--card-border);border-radius:6px;padding:8px 10px;font-size:12px;line-height:1.5;resize:vertical;" placeholder="Professional summary or screening pitch"></textarea>
            </div>
          </div>
        </div>

        <div style="font-size:12px;color:var(--text-muted);">
          <strong>How to use:</strong>
          <ol style="padding-left:18px;margin-top:6px;line-height:1.7;">
            <li>Click <strong>Apply</strong> on any opportunity card.</li>
            <li>When the company's application page opens, click the <strong>AutoFill JobHunt</strong> bookmark on your browser bar.</li>
            <li>All fields, links, and cover notes are filled automatically.</li>
            <li>Solve any CAPTCHA if prompted, and click <strong>Submit</strong>!</li>
          </ol>
        </div>
      </div>

      <div style="display:flex;justify-content:flex-end;padding-top:10px;border-top:1px solid var(--card-border);">
        <button class="btn-applied" onclick="closeBookmarkletGuide()">Got it</button>
      </div>
    </div>
  </div>

  <!-- Modal 3: WhatsApp Bot Connection Guide Modal -->
  <div class="modal-backdrop" id="modal-whatsapp-guide" onclick="if(event.target===this)closeWhatsAppGuide()">
    <div class="modal-card" style="max-width:560px;" role="dialog" aria-modal="true" aria-labelledby="wa-modal-title">
      <div class="modal-header">
        <div style="display:flex;align-items:center;gap:8px;">
          <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>
          </svg>
          <h2 id="wa-modal-title" style="font-size:17px;font-weight:800;color:var(--text-main);">Instant Phone Job Alerts (Telegram &amp; WhatsApp)</h2>
        </div>
        <button class="modal-close-btn" onclick="closeWhatsAppGuide()" aria-label="Close modal">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div style="font-size:13px;color:#c9d1d9;line-height:1.6;display:flex;flex-direction:column;gap:12px;">
        <div style="background:rgba(35,134,54,0.15);border:1px solid #2ea043;border-radius:8px;padding:14px;display:flex;flex-direction:column;gap:10px;">
          <div>
            <strong style="color:#7ee787;display:block;margin-bottom:4px;">Telegram Bot Connected: @ShubhamJobHunt_Bot</strong>
            <span>Instant alerts deliver with 1-click apply links and match scores to your phone in &lt;1 second.</span>
          </div>
          <div>
            <a href="https://t.me/ShubhamJobHunt_Bot" target="_blank" rel="noopener noreferrer" class="btn-apply-link" style="background:#229ed9;text-decoration:none;display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:6px;font-weight:700;font-size:13px;color:#fff;border:none;">
              <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
              <span>Open @ShubhamJobHunt_Bot on Telegram</span>
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          </div>
        </div>

        <div style="background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:14px;">
          <strong style="color:var(--text-main);display:block;margin-bottom:6px;">GitHub Actions Repository Secrets:</strong>
          <p style="margin:0 0 10px 0;font-size:12.5px;color:var(--text-muted);line-height:1.5;">
            To enable automated job alerts, configure your <code>TELEGRAM_BOT_TOKEN</code> and <code>TELEGRAM_CHAT_ID</code> credentials in your repository's GitHub Secrets. Values remain encrypted and are never exposed in client builds or public logs.
          </p>
          <div>
            <a href="https://github.com/shubhaammm08/Job-Hunt/settings/secrets/actions" target="_blank" rel="noopener noreferrer" class="btn-copy-chip" style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;font-size:12px;text-decoration:none;">
              <span>Open GitHub Secrets Settings</span>
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          </div>
        </div>

        <div style="font-size:12px;color:var(--text-muted);">
          <strong>Optional WhatsApp Gateway (CallMeBot):</strong>
          Send <code>I allow callmebot to send me messages</code> to <code>+34 623 78 64 49</code> on WhatsApp if you also want WhatsApp alerts.
        </div>
      </div>

      <div style="display:flex;justify-content:flex-end;padding-top:10px;border-top:1px solid var(--card-border);">
        <button class="btn-applied" onclick="closeWhatsAppGuide()">Done</button>
      </div>
    </div>
  </div>

  <!-- Modal 4: Applied Jobs Tracker Hub -->
  <div class="modal-backdrop" id="modal-applied-tracker" onclick="if(event.target===this)closeAppliedTrackerModal()">
    <div class="modal-card" style="max-width:760px;" role="dialog" aria-modal="true" aria-labelledby="applied-tracker-title">
      <div class="modal-header">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span class="tag tag-applied" style="font-size:11px;">
              <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> APPLIED TRACKER
            </span>
            <span style="font-size:12px;color:var(--text-muted);" id="applied-tracker-count">0 applications</span>
          </div>
          <h2 id="applied-tracker-title" style="font-size:18px;font-weight:800;color:var(--text-main);">Applied Jobs Hub</h2>
        </div>
        <button class="modal-close-btn" onclick="closeAppliedTrackerModal()" aria-label="Close modal">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;align-items:center;padding:10px 14px;background:rgba(0,0,0,0.25);border-radius:8px;border:1px solid var(--card-border);">
        <span style="font-size:12.5px;color:var(--text-muted);">Manage your submitted applications and export records:</span>
        <div style="display:flex;gap:8px;">
          <button class="btn-applied-export" onclick="exportAppliedJobsCsv()" title="Download CSV export">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span>Export CSV</span>
          </button>
          <button class="btn-applied-export" onclick="copyAppliedJobLinks()" title="Copy all links to clipboard">
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            <span>Copy Links</span>
          </button>
        </div>
      </div>

      <div id="applied-tracker-list" style="display:flex;flex-direction:column;gap:10px;max-height:55vh;overflow-y:auto;padding-right:4px;">
        <!-- Dynamically rendered applied jobs -->
      </div>
    </div>
  </div>

  <!-- Global Floating Toast Notification -->
  <div id="global-toast" class="toast-msg"></div>

  <script>
    let appData = {
      jobs: [],
      stats: {},
      profile: {},
      source_health: [],
      digest_html: ""
    };

    let activeChip = 'all';
    const SOURCES_CATALOG = [{"source": "Greenhouse", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596414+00:00"}, {"source": "Ashby", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596439+00:00"}, {"source": "Lever", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596445+00:00"}, {"source": "SmartRecruiters", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596450+00:00"}, {"source": "Workable", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596456+00:00"}, {"source": "Recruitee", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596459+00:00"}, {"source": "Personio", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596463+00:00"}, {"source": "Breezy HR", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596467+00:00"}, {"source": "BambooHR", "category": "direct_ats", "tier": 1, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596470+00:00"}, {"source": "Workday", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.workday.feed_url"], "last_scan": "2026-11-17T05:39:45.596475+00:00"}, {"source": "Teamtailor", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.teamtailor.feed_url"], "last_scan": "2026-11-17T05:39:45.596482+00:00"}, {"source": "Rippling", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.rippling.feed_url"], "last_scan": "2026-11-17T05:39:45.596487+00:00"}, {"source": "Gem", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.gem.feed_url"], "last_scan": "2026-11-17T05:39:45.596491+00:00"}, {"source": "Paylocity", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.paylocity.feed_url"], "last_scan": "2026-11-17T05:39:45.596494+00:00"}, {"source": "JazzHR", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.jazzhr.feed_url"], "last_scan": "2026-11-17T05:39:45.596497+00:00"}, {"source": "Manatal", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.manatal.feed_url"], "last_scan": "2026-11-17T05:39:45.596500+00:00"}, {"source": "Jobvite", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.jobvite.feed_url"], "last_scan": "2026-11-17T05:39:45.596503+00:00"}, {"source": "Phenom", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.phenom.feed_url"], "last_scan": "2026-11-17T05:39:45.596509+00:00"}, {"source": "Homerun", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.homerun.feed_url"], "last_scan": "2026-11-17T05:39:45.596512+00:00"}, {"source": "HireHive", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.hirehive.feed_url"], "last_scan": "2026-11-17T05:39:45.596515+00:00"}, {"source": "JobScore", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.jobscore.feed_url"], "last_scan": "2026-11-17T05:39:45.596518+00:00"}, {"source": "Flatchr", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.flatchr.feed_url"], "last_scan": "2026-11-17T05:39:45.596521+00:00"}, {"source": "Talentadore", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.talentadore.feed_url"], "last_scan": "2026-11-17T05:39:45.596524+00:00"}, {"source": "Jobsoid", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.jobsoid.feed_url"], "last_scan": "2026-11-17T05:39:45.596527+00:00"}, {"source": "PyjamaHR", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.pyjamahr.feed_url"], "last_scan": "2026-11-17T05:39:45.596531+00:00"}, {"source": "Gupy", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.gupy.feed_url"], "last_scan": "2026-11-17T05:39:45.596534+00:00"}, {"source": "Oracle Recruiting", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.oracle_recruiting.feed_url"], "last_scan": "2026-11-17T05:39:45.596537+00:00"}, {"source": "SAP SuccessFactors", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.sap_successfactors.feed_url"], "last_scan": "2026-11-17T05:39:45.596540+00:00"}, {"source": "iCIMS", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.icims.feed_url"], "last_scan": "2026-11-17T05:39:45.596544+00:00"}, {"source": "Pinpoint", "category": "direct_ats", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Enterprise ATS: Add company feed URL in config.yaml under sources.pinpoint.feed_url"], "last_scan": "2026-11-17T05:39:45.596546+00:00"}, {"source": "Remotive", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596550+00:00"}, {"source": "Remote OK", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596554+00:00"}, {"source": "Himalayas", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596564+00:00"}, {"source": "Jobicy", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596568+00:00"}, {"source": "Working Nomads", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596571+00:00"}, {"source": "NoDesk", "category": "remote", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596575+00:00"}, {"source": "Remote.co", "category": "remote", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure REMOTECO_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596585+00:00"}, {"source": "Jobspresso", "category": "remote", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure JOBSPRESSO_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596590+00:00"}, {"source": "Dynamite Jobs", "category": "remote", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure DYNAMITEJOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596594+00:00"}, {"source": "JustRemote", "category": "remote", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure JUSTREMOTE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596598+00:00"}, {"source": "Hacker News Who Is Hiring", "category": "startup", "tier": 3, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": "2026-11-17T05:39:45.596602+00:00"}, {"source": "Wellfound", "category": "startup", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure WELLFOUND_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596606+00:00"}, {"source": "Y Combinator Jobs", "category": "startup", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure YC_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596610+00:00"}, {"source": "Y Combinator Work at a Startup", "category": "startup", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure YC_WORKATASTARTUP_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596615+00:00"}, {"source": "Cutshort", "category": "startup", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure CUTSHORT_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596619+00:00"}, {"source": "Instahyre", "category": "startup", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure INSTAHYRE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596622+00:00"}, {"source": "Product Hunt Jobs", "category": "startup", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure PRODUCTHUNT_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596625+00:00"}, {"source": "LinkedIn", "category": "professional_network", "tier": 2, "status": "HEALTHY", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": [], "last_scan": null}, {"source": "LinkedIn Jobs India", "category": "india_job_board", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596629+00:00"}, {"source": "Indeed India", "category": "india_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596634+00:00"}, {"source": "Naukri", "category": "india_job_board", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596638+00:00"}, {"source": "Naukri Campus", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure NAUKRI_CAMPUS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596642+00:00"}, {"source": "Foundit", "category": "india_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure FOUNDIT_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596646+00:00"}, {"source": "Hirist", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure HIRIST_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596651+00:00"}, {"source": "Shine", "category": "india_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure SHINE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596654+00:00"}, {"source": "TimesJobs", "category": "india_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure TIMESJOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596657+00:00"}, {"source": "Apna", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure APNA_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596661+00:00"}, {"source": "Internshala", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure INTERNSHALA_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596665+00:00"}, {"source": "Unstop", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure UNSTOP_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596669+00:00"}, {"source": "iimjobs", "category": "india_job_board", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure IIMJOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596672+00:00"}, {"source": "Indeed", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596676+00:00"}, {"source": "LinkedIn Jobs", "category": "global_job_board", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596679+00:00"}, {"source": "Glassdoor", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596682+00:00"}, {"source": "ZipRecruiter", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Free activation: Add RAPIDAPI_KEY to GitHub Secrets for 500 free queries/mo across commercial boards."], "last_scan": "2026-11-17T05:39:45.596685+00:00"}, {"source": "Monster", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure MONSTER_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596689+00:00"}, {"source": "CareerBuilder", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure CAREERBUILDER_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596692+00:00"}, {"source": "Dice", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure DICE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596697+00:00"}, {"source": "SimplyHired", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure SIMPLYHIRED_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596700+00:00"}, {"source": "Jooble", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure JOOBLE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596704+00:00"}, {"source": "Adzuna", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure ADZUNA_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596707+00:00"}, {"source": "Jobrapido", "category": "global_job_board", "tier": 4, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure JOBRAPIDO_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596710+00:00"}, {"source": "Freshersworld", "category": "fresher", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure FRESHERSWORLD_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596714+00:00"}, {"source": "Superset", "category": "fresher", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure SUPERSET_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596717+00:00"}, {"source": "FirstNaukri", "category": "fresher", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure FIRSTNAUKRI_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596720+00:00"}, {"source": "Prosple", "category": "fresher", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure PROSPLE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596724+00:00"}, {"source": "Handshake", "category": "fresher", "tier": 3, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure HANDSHAKE_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596727+00:00"}, {"source": "AI Jobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure AI_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596731+00:00"}, {"source": "TopAIJobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure TOP_AI_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596735+00:00"}, {"source": "AI-Jobs.net", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure AI_JOBS_NET_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596738+00:00"}, {"source": "Hugging Face Jobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure HUGGINGFACE_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596741+00:00"}, {"source": "MLOps.community Jobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure MLOPS_COMMUNITY_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596745+00:00"}, {"source": "Data Science Jobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure DATA_SCIENCE_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596749+00:00"}, {"source": "Kaggle Jobs", "category": "ai_specific", "tier": 2, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure KAGGLE_JOBS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596753+00:00"}, {"source": "NVIDIA Careers", "category": "ai_specific", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure NVIDIA_CAREERS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596756+00:00"}, {"source": "OpenAI Careers", "category": "ai_specific", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure OPENAI_CAREERS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596761+00:00"}, {"source": "Anthropic Careers", "category": "ai_specific", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure ANTHROPIC_CAREERS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596765+00:00"}, {"source": "Google DeepMind Careers", "category": "ai_specific", "tier": 1, "status": "CONFIG_REQUIRED", "jobs_found": 0, "jobs_after_filtering": 0, "new_jobs": 0, "duplicates_removed": 0, "errors": ["Requires partner API key: configure DEEPMIND_CAREERS_API_KEY in GitHub Secrets."], "last_scan": "2026-11-17T05:39:45.596768+00:00"}];

    const ICONS = {
      mapPin: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
      source: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
      info: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
      check: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
      external: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
      bolt: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
      copy: `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
      close: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
      searchEmpty: `<svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="var(--text-muted)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`
    };

    /**
     * Infers workplace arrangement (remote, hybrid, onsite, other).
     */
    function inferWorkplaceType(job) {
      if (job.workplace_type) {
        const val = String(job.workplace_type).toLowerCase();
        if (val.includes('remote') || val.includes('wfh')) return 'remote';
        if (val.includes('hybrid') || val.includes('flex')) return 'hybrid';
        if (val.includes('onsite') || val.includes('office')) return 'onsite';
        return 'other';
      }

      const loc = (job.location || '').trim();
      const title = (job.title || '').trim();
      const reason = (job.reason || '').trim();
      const combined = `${loc} ${title} ${reason}`.toLowerCase();

      if (/\b(hybrid|flexible)\b/i.test(combined)) {
        return 'hybrid';
      }

      if (/\b(remote|work from home|wfh|anywhere|telecommute)\b/i.test(combined)) {
        return 'remote';
      }

      if (loc && loc !== 'Not Specified' && loc !== 'Unspecified') {
        return 'onsite';
      }

      return 'other';
    }

    function getWorkplaceLabel(wpType) {
      switch (wpType) {
        case 'remote': return 'Remote';
        case 'hybrid': return 'Hybrid';
        case 'onsite': return 'Onsite';
        default: return 'Other / Unspecified';
      }
    }

    /**
     * Infers platform/ATS source (greenhouse, ashby, lever, remotive, hackernews, remoteok, workingnomads, nodesk, linkedin, naukri, indeed, smartrecruiters, workable, direct_ats, other).
     */
    function inferPlatformSource(job) {
      if (job.platform) {
        const p = String(job.platform).toLowerCase();
        if (p.includes('greenhouse')) return 'greenhouse';
        if (p.includes('ashby')) return 'ashby';
        if (p.includes('lever')) return 'lever';
        if (p.includes('smartrecruiters')) return 'smartrecruiters';
        if (p.includes('workable')) return 'workable';
        if (p.includes('recruitee')) return 'recruitee';
        if (p.includes('personio')) return 'personio';
        if (p.includes('breezy')) return 'breezy';
        if (p.includes('bamboohr')) return 'bamboohr';
        if (p.includes('workday')) return 'workday';
        if (p.includes('remotive')) return 'remotive';
        if (p.includes('remoteok')) return 'remoteok';
        if (p.includes('nodesk')) return 'nodesk';
        if (p.includes('workingnomads') || p.includes('working nomads')) return 'workingnomads';
        if (p.includes('himalayas')) return 'himalayas';
        if (p.includes('jobicy')) return 'jobicy';
        if (p.includes('hacker') || p.includes('hn') || p.includes('ycombinator')) return 'hackernews';
        if (p.includes('linkedin')) return 'linkedin';
        if (p.includes('naukri')) return 'naukri';
        if (p.includes('indeed')) return 'indeed';
        if (p.includes('glassdoor')) return 'glassdoor';
        if (p.includes('wellfound') || p.includes('angel')) return 'wellfound';
        if (p.includes('direct') || p.includes('company')) return 'direct_ats';
        return 'other';
      }

      const url = (job.url || '').trim();
      const jid = (job.job_id || '').toLowerCase();
      const canSrc = (job.canonical_source || '').toLowerCase();
      const sources = Array.isArray(job.sources) ? job.sources.join(' ').toLowerCase() : '';
      const text = `${url} ${jid} ${canSrc} ${sources} ${job.title || ''} ${job.reason || ''}`.toLowerCase();

      let domain = '';
      let search = '';
      try {
        const parsed = new URL(url.startsWith('http') ? url : `https://${url}`);
        domain = parsed.hostname.toLowerCase();
        search = parsed.search.toLowerCase();
      } catch (e) {
        domain = url.toLowerCase();
      }

      if (domain.includes('greenhouse.io') || search.includes('gh_jid') || jid.startsWith('greenhouse:') || canSrc === 'greenhouse' || sources.includes('greenhouse') || text.includes('greenhouse')) {
        return 'greenhouse';
      }

      if (domain.includes('ashbyhq.com') || jid.startsWith('ashby:') || canSrc === 'ashby' || sources.includes('ashby') || text.includes('ashby')) {
        return 'ashby';
      }

      if (domain.includes('lever.co') || jid.startsWith('lever:') || canSrc === 'lever' || sources.includes('lever') || text.includes('lever')) {
        return 'lever';
      }

      if (domain.includes('remotive.com') || domain.includes('remotive.io') || jid.startsWith('remotive:') || canSrc === 'remotive' || sources.includes('remotive') || text.includes('remotive')) {
        return 'remotive';
      }

      if (domain.includes('remoteok.com') || domain.includes('remoteok.io') || jid.startsWith('remoteok:') || canSrc === 'remoteok' || sources.includes('remoteok') || text.includes('remoteok')) {
        return 'remoteok';
      }

      if (domain.includes('workingnomads.com') || jid.startsWith('workingnomads:') || canSrc === 'workingnomads' || sources.includes('workingnomads') || text.includes('workingnomads') || text.includes('working nomads')) {
        return 'workingnomads';
      }

      if (domain.includes('nodesk.co') || jid.startsWith('nodesk:') || canSrc === 'nodesk' || sources.includes('nodesk') || text.includes('nodesk')) {
        return 'nodesk';
      }

      if (domain.includes('news.ycombinator.com') || domain.includes('ycombinator.com') || jid.startsWith('hn:') || jid.startsWith('hackernews:') || text.includes('hacker news') || text.includes('ycombinator')) {
        return 'hackernews';
      }

      if (domain.includes('smartrecruiters.com') || jid.startsWith('smartrecruiters:') || canSrc === 'smartrecruiters' || sources.includes('smartrecruiters') || text.includes('smartrecruiters')) {
        return 'smartrecruiters';
      }

      if (domain.includes('workable.com') || jid.startsWith('workable:') || canSrc === 'workable' || sources.includes('workable') || text.includes('workable')) {
        return 'workable';
      }

      if (domain.includes('recruitee.com') || jid.startsWith('recruitee:') || canSrc === 'recruitee' || sources.includes('recruitee')) {
        return 'recruitee';
      }

      if (domain.includes('personio.de') || domain.includes('personio.com') || jid.startsWith('personio:') || canSrc === 'personio' || sources.includes('personio')) {
        return 'personio';
      }

      if (domain.includes('breezy.hr') || jid.startsWith('breezy:') || canSrc === 'breezy' || sources.includes('breezy')) {
        return 'breezy';
      }

      if (domain.includes('bamboohr.com') || jid.startsWith('bamboohr:') || canSrc === 'bamboohr' || sources.includes('bamboohr')) {
        return 'bamboohr';
      }

      if (domain.includes('myworkdayjobs.com') || jid.startsWith('workday:') || canSrc === 'workday' || sources.includes('workday')) {
        return 'workday';
      }

      if (domain.includes('linkedin.com') || jid.startsWith('linkedin:') || jid.startsWith('linkedin_india:') || jid.startsWith('linkedin_global:') || canSrc.startsWith('linkedin') || sources.includes('linkedin')) {
        return 'linkedin';
      }

      if (domain.includes('naukri.com') || jid.startsWith('naukri:') || jid.startsWith('naukri_campus:') || canSrc.startsWith('naukri') || sources.includes('naukri')) {
        return 'naukri';
      }

      if (domain.includes('indeed.com') || jid.startsWith('indeed:') || jid.startsWith('indeed_india:') || canSrc.startsWith('indeed') || sources.includes('indeed')) {
        return 'indeed';
      }

      if (domain.includes('himalayas.app') || jid.startsWith('himalayas:') || canSrc === 'himalayas' || sources.includes('himalayas')) {
        return 'himalayas';
      }

      if (domain.includes('jobicy.com') || jid.startsWith('jobicy:') || canSrc === 'jobicy' || sources.includes('jobicy')) {
        return 'jobicy';
      }

      if (domain.includes('wellfound.com') || domain.includes('angel.co') || jid.startsWith('wellfound:') || canSrc === 'wellfound' || sources.includes('wellfound')) {
        return 'wellfound';
      }

      if (domain.includes('glassdoor.com') || jid.startsWith('glassdoor:') || canSrc === 'glassdoor' || sources.includes('glassdoor')) {
        return 'glassdoor';
      }

      if (job.ats || domain.includes('careers.') || domain.includes('jobs.') || url.includes('/careers') || url.includes('/jobs')) {
        return 'direct_ats';
      }

      return 'other';
    }

    function getPlatformLabel(platformKey) {
      switch (platformKey) {
        case 'greenhouse': return 'Greenhouse';
        case 'ashby': return 'Ashby';
        case 'lever': return 'Lever';
        case 'remotive': return 'Remotive';
        case 'hackernews': return 'Hacker News';
        case 'remoteok': return 'Remote OK';
        case 'nodesk': return 'NoDesk';
        case 'workingnomads': return 'Working Nomads';
        case 'linkedin': return 'LinkedIn';
        case 'naukri': return 'Naukri';
        case 'indeed': return 'Indeed';
        case 'smartrecruiters': return 'SmartRecruiters';
        case 'workable': return 'Workable';
        case 'recruitee': return 'Recruitee';
        case 'personio': return 'Personio';
        case 'breezy': return 'Breezy HR';
        case 'bamboohr': return 'BambooHR';
        case 'workday': return 'Workday';
        case 'himalayas': return 'Himalayas';
        case 'jobicy': return 'Jobicy';
        case 'wellfound': return 'Wellfound';
        case 'glassdoor': return 'Glassdoor';
        case 'direct_ats': return 'Direct ATS / Company';
        default: return 'Other / Unspecified';
      }
    }

    function extractLinkedInJobId(rawUrlOrId) {
      const s = String(rawUrlOrId || '').trim();
      if (!s) return '';
      if (/^\d+$/.test(s)) return s;
      const prefixMatch = s.match(/linkedin[^:]*:(\d+)/i);
      if (prefixMatch && prefixMatch[1]) return prefixMatch[1];
      const viewMatch = s.match(/\/jobs\/view\/(?:[a-zA-Z0-9\-_]+-)?(\d+)/i);
      if (viewMatch && viewMatch[1]) return viewMatch[1];
      const simpleViewMatch = s.match(/\/view\/(?:[a-zA-Z0-9\-_]+-)?(\d+)/i);
      if (simpleViewMatch && simpleViewMatch[1]) return simpleViewMatch[1];
      const queryMatch = s.match(/[?&]currentJobId=(\d+)/i);
      if (queryMatch && queryMatch[1]) return queryMatch[1];
      const urnMatch = s.match(/jobPosting:(\d+)/i);
      if (urnMatch && urnMatch[1]) return urnMatch[1];
      const trailingMatch = s.match(/(\d{6,})/);
      if (trailingMatch && trailingMatch[1]) return trailingMatch[1];
      return '';
    }

    function isLinkedInJob(job) {
      if (!job) return false;
      if (typeof inferPlatformSource === 'function' && inferPlatformSource(job) === 'linkedin') return true;
      const jid = String(job.job_id || '').toLowerCase();
      const url = String(job.url || '').toLowerCase();
      const applyUrl = String(job.apply_url || '').toLowerCase();
      const plat = String(job.platform || '').toLowerCase();
      const canSrc = String(job.canonical_source || '').toLowerCase();
      return jid.startsWith('linkedin') ||
             url.includes('linkedin.com') ||
             applyUrl.includes('linkedin.com') ||
             plat === 'linkedin' ||
             canSrc === 'linkedin';
    }

    function isLinkedInUrl(url) {
      const s = String(url || '').toLowerCase();
      return s.includes('linkedin.com/jobs/view/') || s.includes('linkedin.com');
    }

    function getLinkedInPostUrl(job) {
      if (!job) return '';
      const cleanId = extractLinkedInJobId(job.job_id) ||
                      extractLinkedInJobId(job.url) ||
                      extractLinkedInJobId(job.apply_url);
      if (cleanId) {
        return `https://www.linkedin.com/jobs/view/${cleanId}`;
      }
      const rawUrl = String(job.url || job.apply_url || '').trim();
      if (rawUrl.includes('linkedin.com/jobs/view/')) {
        return rawUrl.split('?')[0].split('#')[0];
      }
      if (rawUrl && rawUrl !== '#') {
        return rawUrl;
      }
      return '';
    }

    function setQuickChip(chipType) {
      const scoreSel = document.getElementById('filter-score');
      const statusSel = document.getElementById('filter-status');
      const familySel = document.getElementById('filter-family');
      const workplaceSel = document.getElementById('filter-workplace');
      const platformSel = document.getElementById('filter-platform');

      // Toggle back to 'all' if tapping already active chip
      if (activeChip === chipType && chipType !== 'all') {
        chipType = 'all';
      }
      activeChip = chipType;

      // Reset all dropdowns
      scoreSel.value = 'all';
      statusSel.value = 'all';
      familySel.value = 'all';
      workplaceSel.value = 'all';
      platformSel.value = 'all';

      switch (chipType) {
        case 'applied': statusSel.value = 'applied'; break;
        case 'high': scoreSel.value = '8'; break;
        case 'rec': scoreSel.value = '6'; break;
        case 'unapplied': statusSel.value = 'unapplied'; break;
        case 'data': familySel.value = 'DATA'; break;
        case 'ai': familySel.value = 'AI_CORE'; break;
        case 'python': familySel.value = 'SOFTWARE'; break;
        case 'remote': workplaceSel.value = 'remote'; break;
        case 'hybrid': workplaceSel.value = 'hybrid'; break;
        case 'onsite': workplaceSel.value = 'onsite'; break;
        case 'greenhouse': platformSel.value = 'greenhouse'; break;
        case 'ashby': platformSel.value = 'ashby'; break;
        case 'lever': platformSel.value = 'lever'; break;
        case 'linkedin': platformSel.value = 'linkedin'; break;
        case 'remotive': platformSel.value = 'remotive'; break;
        case 'hackernews': platformSel.value = 'hackernews'; break;
        case 'other_plat': platformSel.value = 'other'; break;
        case 'all':
        default:
          break;
      }

      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      const activeEl = document.getElementById('chip-' + chipType);
      if (activeEl) activeEl.classList.add('active');

      renderJobs();
    }

    function syncChipAndRender() {
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      activeChip = 'custom';
      renderJobs();
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');
      
      const targetPanel = document.getElementById('tab-' + tabId);
      if (targetPanel) targetPanel.classList.add('active');

      if (tabId === 'digest') {
        renderDigest();
      } else if (tabId === 'sources') {
        renderSources();
        fetchLinkedInStatus();
      }
    }

    function syncAppliedStateWithStorage() {
      try {
        const storedMeta = JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}');
        const legacyList = JSON.parse(localStorage.getItem('jobhunt_applied') || '[]');

        legacyList.forEach(id => {
          if (!storedMeta[id]) {
            storedMeta[id] = { job_id: id, applied_at: new Date().toISOString() };
          }
        });

        if (appData && Array.isArray(appData.jobs)) {
          appData.jobs.forEach(j => {
            if (storedMeta[j.job_id] || legacyList.includes(j.job_id) || j.applied) {
              j.applied = true;
              if (!storedMeta[j.job_id]) {
                storedMeta[j.job_id] = {
                  job_id: j.job_id,
                  applied_at: new Date().toISOString(),
                  title: j.title || '',
                  company: j.company || '',
                  location: j.location || '',
                  url: isLinkedInJob(j) ? (getLinkedInPostUrl(j) || j.url || '') : (j.url || ''),
                  score: j.score || 0.0,
                  platform: inferPlatformSource(j)
                };
              }
              if (!legacyList.includes(j.job_id)) {
                legacyList.push(j.job_id);
              }
            }
          });

          localStorage.setItem('jobhunt_applied_jobs', JSON.stringify(storedMeta));
          localStorage.setItem('jobhunt_applied', JSON.stringify(legacyList));

          if (appData.stats) {
            appData.stats.applied = appData.jobs.filter(j => j.applied).length;
          }
        }
      } catch (e) {
        console.warn('Could not sync applied state with storage', e);
      }
    }

    async function loadData() {
      // 1. Initial pre-bundled payload if available
      if (window.INITIAL_DATA && window.INITIAL_DATA.jobs && window.INITIAL_DATA.jobs.length) {
        appData = window.INITIAL_DATA;
        syncAppliedStateWithStorage();
        renderAll();
      }
      // 2. Query local server API if running locally
      try {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          const res = await fetch('/api/data');
          if (res.ok) {
            appData = await res.json();
            syncAppliedStateWithStorage();
            renderAll();
          }
        }
      } catch (err) {
        // Static mode or offline fallback
        if (!window.INITIAL_DATA) {
          loadStaticFallback();
        }
      }
      fetchLinkedInStatus();
    }

    function syncPlatformFilterOptions() {
      const select = document.getElementById('filter-platform');
      if (!select || !appData.jobs) return;
      const currentVal = select.value;
      const activePlatforms = new Set();
      appData.jobs.forEach(j => {
        const plat = inferPlatformSource(j);
        if (plat && plat !== 'all') {
          activePlatforms.add(plat);
        }
      });
      activePlatforms.forEach(plat => {
        let opt = select.querySelector(`option[value="${plat}"]`);
        if (!opt) {
          opt = document.createElement('option');
          opt.value = plat;
          opt.textContent = getPlatformLabel(plat);
          const otherOpt = select.querySelector('option[value="other"]');
          if (otherOpt) {
            select.insertBefore(opt, otherOpt);
          } else {
            select.appendChild(opt);
          }
        }
      });
      select.value = currentVal;
    }

    function renderAll() {
      syncPlatformFilterOptions();
      renderStats();
      renderJobs();
      renderSources();
      renderProfile();
      renderDigest();
    }

    function renderStats() {
      const stats = appData.stats || {};
      const appliedCount = (appData.jobs || []).filter(j => j.applied).length;
      stats.applied = appliedCount;
      
      document.getElementById('metric-total').innerText = stats.total || (appData.jobs || []).length || 0;
      document.getElementById('metric-recommended').innerText = stats.recommended || (appData.jobs || []).filter(j => (parseFloat(j.score) || 0) >= 6.0).length || 0;
      document.getElementById('metric-applied').innerText = appliedCount;
      document.getElementById('metric-sources').innerText = stats.sources_count || 87;
      
      const totalJobs = (appData.jobs && appData.jobs.length) ? appData.jobs.length : (stats.total || 0);
      const rate = totalJobs ? Math.round((appliedCount / totalJobs) * 100) : 0;
      document.getElementById('metric-applied-rate').innerText = `${rate}% applied`;
      document.getElementById('tab-count-jobs').innerText = totalJobs;

      const chipCount = document.getElementById('chip-count-applied');
      if (chipCount) chipCount.innerText = appliedCount;
      const modalCount = document.getElementById('applied-tracker-count');
      if (modalCount) modalCount.innerText = `${appliedCount} application${appliedCount === 1 ? '' : 's'}`;
    }

    function renderJobs() {
      const query = (document.getElementById('search-input').value || '').toLowerCase().trim();
      const scoreFilter = document.getElementById('filter-score').value;
      const statusFilter = document.getElementById('filter-status').value;
      const familyFilter = document.getElementById('filter-family').value;
      const workplaceFilter = document.getElementById('filter-workplace').value;
      const platformFilter = document.getElementById('filter-platform').value;

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

        if (workplaceFilter !== 'all') {
          const wp = inferWorkplaceType(j);
          if (wp !== workplaceFilter) return false;
        }

        if (platformFilter !== 'all') {
          const plat = inferPlatformSource(j);
          if (plat !== platformFilter) return false;
        }

        return true;
      });

      const statusSuffix = (statusFilter === 'applied') ? ' (Applied Jobs)' : ((statusFilter === 'unapplied') ? ' (Unapplied Jobs)' : '');
      document.getElementById('results-count').innerText = `Showing ${filtered.length} of ${(appData.jobs || []).length} opportunities${statusSuffix}`;

      if (!filtered.length) {
        const isAppliedFilter = statusFilter === 'applied';
        const emptyMsg = isAppliedFilter
          ? 'No applied jobs recorded yet'
          : 'No matching opportunities found';
        const emptySub = isAppliedFilter
          ? 'Click "Apply" or "Mark Applied" on any opportunity card to track your applications here.'
          : 'Try adjusting your filters or search keywords.';
        listContainer.innerHTML = `
          <div style="text-align:center;padding:50px 20px;color:var(--text-muted);background:var(--card-bg);border:1px dashed var(--card-border);border-radius:12px;">
            <div style="display:flex;justify-content:center;margin-bottom:8px;">${ICONS.searchEmpty}</div>
            <div style="font-weight:600;color:var(--text-main);">${escapeHtml(emptyMsg)}</div>
            <div style="font-size:12px;margin-top:4px;">${escapeHtml(emptySub)}</div>
            ${isAppliedFilter ? `<button class="btn-applied-export" style="margin-top:14px;background:var(--accent-blue);color:#fff;border-color:transparent;" onclick="setQuickChip('all')">View All Opportunities</button>` : ''}
          </div>
        `;
        return;
      }

      listContainer.innerHTML = filtered.map(j => {
        const score = parseFloat(j.score) || 0.0;
        const scoreClass = score >= 8.0 ? 'score-high' : (score >= 6.0 ? 'score-mid' : 'score-low');
        const appliedClass = j.applied ? 'is-applied' : '';
        const btnAppliedHtml = j.applied ? `${ICONS.check} Applied` : 'Mark Applied';
        const btnAppliedClass = j.applied ? 'btn-applied active' : 'btn-applied';
        const appliedBadgeHtml = j.applied ? `<span class="tag tag-applied">${ICONS.check} APPLIED</span>` : '';

        const inferredPlat = inferPlatformSource(j);
        const platformLabel = getPlatformLabel(inferredPlat);
        const inferredWp = inferWorkplaceType(j);
        const workplaceLabel = getWorkplaceLabel(inferredWp);

        const isLI = isLinkedInJob(j);
        const targetUrl = isLI ? (getLinkedInPostUrl(j) || j.url || '#') : (j.url || '#');

        const familiesHtml = (j.role_families || []).slice(0, 2).map(f => `<span class="tag tag-family">${escapeHtml(f)}</span>`).join('');
        const skillsHtml = (j.matched_skills || []).slice(0, 3).map(s => `<span class="tag">${escapeHtml(s)}</span>`).join('');
        const sourcesNote = (j.sources && j.sources.length > 1) ? ` · Found on: ${j.sources.join(', ')}` : '';

        return `
          <div class="job-card ${appliedClass}" 
               id="card-${j.job_id}" 
               role="link" 
               tabindex="0" 
               onclick="handleCardClick(event, '${escapeHtml(targetUrl)}', '${j.job_id}')"
               onkeydown="if(event.key==='Enter'||event.key===' '){if(!event.target.closest('button,a')){event.preventDefault();handleCardClick(event, '${escapeHtml(targetUrl)}', '${j.job_id}');}}">
            <div class="job-header">
              <div class="job-title-area">
                <div class="job-title">${escapeHtml(j.title || 'Untitled')}</div>
                <div class="job-meta-line">
                  <span class="job-company">${escapeHtml(j.company || 'Unknown')}</span>
                  <span class="job-location">${ICONS.mapPin} ${escapeHtml(j.location || 'Not Specified')}</span>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                ${appliedBadgeHtml}
                <span class="score-badge ${scoreClass}">${score.toFixed(1)} Match</span>
              </div>
            </div>

            <div class="job-tags">
              <span class="tag tag-source tag-src-${inferredPlat}">${ICONS.source} ${escapeHtml(platformLabel)}</span>
              <span class="tag tag-workplace tag-wp-${inferredWp}">${escapeHtml(workplaceLabel)}</span>
              ${familiesHtml}
              ${skillsHtml}
            </div>

            ${j.reason ? `<div class="job-reason">${ICONS.info} <span><strong>Match Rationale:</strong> ${escapeHtml(j.reason)}</span></div>` : ''}

            <div class="job-actions">
              <span class="job-date">Seen: ${j.first_seen ? j.first_seen.split('T')[0] : 'Today'}${escapeHtml(sourcesNote)}</span>
              <div class="action-group">
                <button class="btn-kit" 
                        title="Auto-Fill Application Kit" 
                        onclick="event.stopPropagation(); openApplyKit('${j.job_id}', event);">
                  ${ICONS.bolt} Kit
                </button>
                <button class="${btnAppliedClass}" 
                        onclick="event.stopPropagation(); toggleApplied('${j.job_id}', event);">
                  ${btnAppliedHtml}
                </button>
                <a href="${escapeHtml(targetUrl)}" 
                   target="_blank" 
                   rel="noopener noreferrer" 
                   class="btn-apply-link" 
                   title="${isLI ? '1-Click Apply on LinkedIn' : 'Apply'}" 
                   onclick="event.stopPropagation(); handleApplyCardLink('${j.job_id}', '${escapeHtml(targetUrl)}', event);">
                  Apply ${ICONS.external}
                </a>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function handleCardClick(event, url, jobId) {
      if (event && event.target && event.target.closest('button, a')) {
        return;
      }
      if (!url || url === '#') {
        showToast('Application link not available for this role.');
        return;
      }
      window.open(url, '_blank', 'noopener,noreferrer');
    }

    function getPreferredBrowser() {
      return localStorage.getItem('jobhunt_apply_browser') || 'default';
    }

    function savePreferredBrowser(val) {
      if (!val) return;
      localStorage.setItem('jobhunt_apply_browser', val);
      const sel = document.getElementById('kit-browser-select');
      if (sel) sel.value = val;
    }

    function launchJobInBrowser(url, browserPref) {
      if (!url || url === '#') return;
      window.open(url, '_blank', 'noopener,noreferrer');
    }

    function handleApplyCardLink(jobId, url, event) {
      if (event) {
        event.stopPropagation();
      }
      handleApplyClick(jobId, url, event);
      const isLI = isLinkedInUrl(url) || (jobId && String(jobId).toLowerCase().startsWith('linkedin'));
      if (isLI) {
        // Direct navigation to LinkedIn post in a new tab:
        // Native click on target="_blank" navigates automatically without backend API.
        // If event default was prevented, explicitly open the URL in a new tab.
        if (event && event.defaultPrevented) {
          window.open(url, '_blank', 'noopener,noreferrer');
        }
        return;
      }
      if (event && event.defaultPrevented) {
        launchJobInBrowser(url);
      }
    }

    async function toggleApplied(jobId, event) {
      if (event) {
        event.stopPropagation();
        if (event.stopImmediatePropagation) event.stopImmediatePropagation();
      }
      const job = (appData.jobs || []).find(j => j.job_id === jobId);
      if (!job) return;
      
      job.applied = !job.applied;

      // Unconditionally persist to localStorage immediately
      try {
        const storedMeta = JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}');
        const legacyList = JSON.parse(localStorage.getItem('jobhunt_applied') || '[]');
        
        if (job.applied) {
          storedMeta[jobId] = {
            job_id: jobId,
            applied_at: new Date().toISOString(),
            title: job.title || '',
            company: job.company || '',
            location: job.location || '',
            url: isLinkedInJob(job) ? (getLinkedInPostUrl(job) || job.url || '') : (job.url || ''),
            score: job.score || 0.0,
            platform: inferPlatformSource(job)
          };
          if (!legacyList.includes(jobId)) legacyList.push(jobId);
          showToast(`Marked "${job.title || 'Role'}" as Applied!`);
        } else {
          delete storedMeta[jobId];
          const idx = legacyList.indexOf(jobId);
          if (idx > -1) legacyList.splice(idx, 1);
          showToast(`Unmarked "${job.title || 'Role'}" from Applied.`);
        }
        localStorage.setItem('jobhunt_applied_jobs', JSON.stringify(storedMeta));
        localStorage.setItem('jobhunt_applied', JSON.stringify(legacyList));
      } catch (e) {
        console.warn('Could not save applied state to localStorage', e);
      }

      if (appData.stats) {
        appData.stats.applied = (appData.jobs || []).filter(j => j.applied).length;
      }
      renderStats();
      renderJobs();

      const modalTracker = document.getElementById('modal-applied-tracker');
      if (modalTracker && modalTracker.classList.contains('open')) {
        renderAppliedTrackerList();
      }

      // If running with local python server on localhost, notify API silently
      try {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          fetch('/api/toggle-applied', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId })
          }).catch(() => {});
        }
      } catch (err) {}
    }

    function openAppliedTrackerModal() {
      renderAppliedTrackerList();
      const m = document.getElementById('modal-applied-tracker');
      if (m) m.classList.add('open');
    }

    function closeAppliedTrackerModal() {
      const m = document.getElementById('modal-applied-tracker');
      if (m) m.classList.remove('open');
    }

    function renderAppliedTrackerList() {
      const container = document.getElementById('applied-tracker-list');
      const countEl = document.getElementById('applied-tracker-count');
      if (!container) return;

      const appliedJobs = (appData.jobs || []).filter(j => j.applied);
      if (countEl) countEl.innerText = `${appliedJobs.length} application${appliedJobs.length === 1 ? '' : 's'}`;

      if (!appliedJobs.length) {
        container.innerHTML = `
          <div style="text-align:center;padding:40px 16px;color:var(--text-muted);border:1px dashed var(--card-border);border-radius:10px;">
            <div style="display:flex;justify-content:center;margin-bottom:8px;">${ICONS.searchEmpty}</div>
            <div style="font-weight:600;color:var(--text-main);font-size:14px;">No Applied Jobs Recorded Yet</div>
            <div style="font-size:12px;margin-top:4px;">When you click "Apply" or "Mark Applied" on any job card, it will appear here permanently.</div>
          </div>
        `;
        return;
      }

      const storedMeta = JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}');

      container.innerHTML = appliedJobs.map(j => {
        const meta = storedMeta[j.job_id] || {};
        const appliedDate = meta.applied_at ? new Date(meta.applied_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recorded';
        const inferredPlat = inferPlatformSource(j);
        const platformLabel = getPlatformLabel(inferredPlat);
        const score = parseFloat(j.score) || 0.0;
        const scoreClass = score >= 8.0 ? 'score-high' : (score >= 6.0 ? 'score-mid' : 'score-low');
        const targetUrl = isLinkedInJob(j) ? (getLinkedInPostUrl(j) || j.url || '#') : (j.url || '#');

        return `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 14px;background:rgba(255,255,255,0.02);border:1px solid var(--card-border);border-radius:10px;flex-wrap:wrap;">
            <div style="min-width:0;flex:1;">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;flex-wrap:wrap;">
                <span class="tag tag-source tag-src-${inferredPlat}">${escapeHtml(platformLabel)}</span>
                <span class="score-badge ${scoreClass}" style="font-size:11px;padding:2px 6px;">${score.toFixed(1)} Match</span>
                <span style="font-size:11px;color:var(--text-muted);">${ICONS.clock} ${appliedDate}</span>
              </div>
              <div style="font-size:14px;font-weight:700;color:var(--text-main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(j.title || 'Untitled')}</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">${escapeHtml(j.company || 'Unknown')} · ${escapeHtml(j.location || 'Remote')}</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center;flex-shrink:0;">
              <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" class="btn-applied-export" style="background:var(--accent-green);color:#fff;border-color:transparent;" title="Open Job Application">
                Open ${ICONS.external}
              </a>
              <button class="btn-applied-export" onclick="toggleApplied('${j.job_id}'); renderAppliedTrackerList();" title="Remove from applied">
                Remove
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function exportAppliedJobsCsv() {
      const appliedJobs = (appData.jobs || []).filter(j => j.applied);
      if (!appliedJobs.length) {
        showToast('No applied jobs to export.');
        return;
      }
      const storedMeta = JSON.parse(localStorage.getItem('jobhunt_applied_jobs') || '{}');
      const rows = [
        ['Job ID', 'Title', 'Company', 'Location', 'Platform', 'Score', 'Applied Date', 'URL']
      ];
      appliedJobs.forEach(j => {
        const meta = storedMeta[j.job_id] || {};
        const appliedDate = meta.applied_at || '';
        const plat = inferPlatformSource(j);
        const targetUrl = isLinkedInJob(j) ? (getLinkedInPostUrl(j) || j.url || '') : (j.url || '');
        rows.push([
          j.job_id || '',
          (j.title || '').replace(/"/g, '""'),
          (j.company || '').replace(/"/g, '""'),
          (j.location || '').replace(/"/g, '""'),
          plat,
          j.score || '0.0',
          appliedDate,
          targetUrl
        ]);
      });

      const csvContent = "data:text/csv;charset=utf-8," + rows.map(r => r.map(f => `"${f}"`).join(',')).join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `applied_jobs_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast(`Exported ${appliedJobs.length} applied jobs to CSV!`);
    }

    function copyAppliedJobLinks() {
      const appliedJobs = (appData.jobs || []).filter(j => j.applied);
      if (!appliedJobs.length) {
        showToast('No applied jobs to copy.');
        return;
      }
      const links = appliedJobs.map(j => {
        const targetUrl = isLinkedInJob(j) ? (getLinkedInPostUrl(j) || j.url || '') : (j.url || '');
        return `${j.title || 'Role'} @ ${j.company || 'Company'}: ${targetUrl}`;
      }).join('\n');

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(links).then(() => {
          showToast(`Copied ${appliedJobs.length} job links to clipboard!`);
        }).catch(() => {
          showToast('Failed to copy links to clipboard.');
        });
      } else {
        showToast('Clipboard access not supported in this browser.');
      }
    }

    function handleApplyClick(jobId, url, event) {
      const job = (appData.jobs || []).find(j => j.job_id === jobId);
      if (job) {
        if (!job.applied) {
          toggleApplied(jobId);
        }
        const note = generateCoverNote(job);
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(note).then(() => {
            showToast(`Applied! Tailored Cover Note for ${job.company || 'Role'} copied to clipboard.`);
          }).catch(() => {
            showToast(`Applied! Opening application page...`);
          });
        }
      }
    }

    let currentKitJob = null;

    function openApplyKit(jobId, event) {
      if (event) {
        event.stopPropagation();
        if (event.stopImmediatePropagation) event.stopImmediatePropagation();
      }
      const job = (appData.jobs || []).find(j => j.job_id === jobId);
      if (!job) return;
      currentKitJob = job;

      document.getElementById('kit-modal-title').innerText = `${job.title || 'Role'} at ${job.company || 'Company'}`;
      document.getElementById('kit-modal-meta').innerText = `${job.location || 'Location Not Specified'} · Match Score: ${(job.score || 0).toFixed(1)}/10`;

      const coverText = generateCoverNote(job);
      const hookText = `Hi, I am Shubham Sunil Kadam, a Computer Engineering graduate specializing in Data Analytics, Python, and ETL automation. I built AI-driven data pipelines and interactive BI dashboards for Honda sales analytics, reducing manual reporting effort by 80%. Excited to apply for the ${job.title || 'opening'} at ${job.company || 'your company'}!`;

      document.getElementById('kit-cover-note').value = coverText;
      document.getElementById('kit-pitch-hook').value = hookText;

      const browserSelect = document.getElementById('kit-browser-select');
      if (browserSelect) {
        browserSelect.value = getPreferredBrowser();
      }

      const launchBtn = document.getElementById('kit-launch-btn');
      launchBtn.onclick = () => {
        const pref = document.getElementById('kit-browser-select') ? document.getElementById('kit-browser-select').value : getPreferredBrowser();
        savePreferredBrowser(pref);
        const isLI = isLinkedInJob(job);
        const targetJobUrl = isLI ? (getLinkedInPostUrl(job) || job.url || '#') : (job.url || '#');
        handleApplyClick(job.job_id, targetJobUrl);
        if (targetJobUrl && targetJobUrl !== '#') {
          if (isLI) {
            window.open(targetJobUrl, '_blank', 'noopener,noreferrer');
          } else {
            launchJobInBrowser(targetJobUrl, pref);
          }
        }

        // Keep the kit open for copy-pasting into the separate browser window!
        const bName = isLI ? 'LinkedIn New Tab' : (pref === 'edge' ? 'Microsoft Edge' : pref === 'brave' ? 'Brave' : pref === 'window' ? 'Companion Window' : 'New Tab');
        document.getElementById('kit-modal-meta').innerHTML = `<span style="color:#3fb950;font-weight:700;">Active in ${bName}</span> · Kit remains open! Tap chips below to copy-paste.`;
        showToast(`Job opened in ${bName}! Cover note copied to clipboard.`);
      };

      document.getElementById('modal-apply-kit').classList.add('open');
    }

    function closeApplyKit() {
      const modal = document.getElementById('modal-apply-kit');
      if (modal) modal.classList.remove('open');
    }

    function openBookmarkletGuide() {
      const guideModal = document.getElementById('modal-bookmarklet-guide');
      if (guideModal) {
        const profile = getApplicantProfile();
        loadAutofillForm(profile);
        updateBookmarkletCode(profile);
        guideModal.classList.add('open');
      }
    }

    function closeBookmarkletGuide() {
      const guideModal = document.getElementById('modal-bookmarklet-guide');
      if (guideModal) guideModal.classList.remove('open');
    }

    function openWhatsAppGuide() {
      const waModal = document.getElementById('modal-whatsapp-guide');
      if (waModal) waModal.classList.add('open');
    }

    function closeWhatsAppGuide() {
      const waModal = document.getElementById('modal-whatsapp-guide');
      if (waModal) waModal.classList.remove('open');
    }

    function copyFieldValue(text, btn) {
      const applyCopiedState = () => {
        if (!btn) return;
        const origText = btn.innerHTML;
        btn.innerHTML = `${ICONS.check} Copied!`;
        btn.classList.add('copied');
        setTimeout(() => {
          btn.innerHTML = origText;
          btn.classList.remove('copied');
        }, 2000);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(applyCopiedState).catch(() => {
          fallbackCopy(text, applyCopiedState);
        });
      } else {
        fallbackCopy(text, applyCopiedState);
      }
    }

    function fallbackCopy(text, onSuccess) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        if (onSuccess) onSuccess();
      } catch (err) {
        console.error('Fallback copy failed:', err);
      }
    }

    function copyAutofillField(inputId, btn) {
      const el = document.getElementById(inputId);
      if (!el) return;
      const val = el.value || '';
      copyFieldValue(val, btn);
      showToast('Copied to clipboard!');
    }

    function showToast(msg) {
      const toast = document.getElementById('global-toast');
      if (!toast) return;
      toast.innerText = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3800);
    }

    function generateCoverNote(job) {
      if (job.draft && job.draft.cover_note) {
        return job.draft.cover_note;
      }
      return `Dear Hiring Team at ${job.company || 'the company'},\n\nI am applying for the ${job.title || 'opening'}. As a Computer Engineering graduate from Vidyavardhini College of Engineering specializing in Data Analytics, Python, and SQL, I bring hands-on experience building automated ETL pipelines, analytical dashboards, and AI agent workflows.\n\nIn my previous projects, I built an end-to-end data pipeline and Power BI dashboard for Honda motorcycle sales analytics, automating repetitive processing and reducing manual effort by 80%. I also engineered real-time applications and speech emotion recognition models using Python and Scikit-learn.\n\nI would welcome the opportunity to discuss how my technical skills in Python, SQL, and data automation can add value to ${job.company || 'your team'}.\n\nThank you for your time and consideration.\n\nSincerely,\nShubham Sunil Kadam\nssk080204@gmail.com | Mumbai, India`;
    }

    const DEFAULT_APPLICANT_PROFILE = {
      firstName: "Shubham",
      lastName: "Kadam",
      fullName: "Shubham Sunil Kadam",
      email: "ssk080204@gmail.com",
      phone: "+918169832448",
      location: "Mumbai Metropolitan Region / Remote",
      linkedin: "https://www.linkedin.com/in/shubham-kadam-data/",
      github: "https://github.com/shubhaammm08",
      portfolio: "https://shubhaammm08.github.io/Job-Hunt/",
      noticePeriod: "Immediate / 0-15 days",
      workAuth: "Yes",
      summary: "AI & Software Engineer specializing in GenAI/LLMs, API & backend development (FastAPI, Flask, Node.js), Full-Stack (React), Mobile (Flutter), workflow automation (n8n, Docker, CI/CD), and ML."
    };

    const AUTOFIL_STORAGE_KEY = 'jobhunt_autofill_profile';
    let BOOKMARKLET_CODE = '';

    function getApplicantProfile() {
      try {
        const saved = localStorage.getItem(AUTOFIL_STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          return Object.assign({}, DEFAULT_APPLICANT_PROFILE, parsed);
        }
      } catch (e) {
        console.error('Error loading applicant profile from localStorage:', e);
      }
      return Object.assign({}, DEFAULT_APPLICANT_PROFILE);
    }

    function generateBookmarkletScript(profile) {
      const p = {
        f: profile.firstName || '',
        l: profile.lastName || '',
        n: profile.fullName || '',
        e: profile.email || '',
        p: profile.phone || '',
        loc: profile.location || '',
        li: profile.linkedin || '',
        gh: profile.github || '',
        w: profile.portfolio || '',
        np: profile.noticePeriod || '',
        wa: profile.workAuth || '',
        c: profile.summary || ''
      };
      const pJson = JSON.stringify(p);

      return `javascript:(function(){const p=${pJson};function t(el,v){if(!el||el.disabled||el.readOnly||!v)return;el.focus();el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));el.dispatchEvent(new Event('blur',{bubbles:true}));}let c=0;document.querySelectorAll('input,textarea,select').forEach(i=>{if(i.type==='hidden'||i.type==='file'||i.type==='submit')return;const k=(i.name+' '+i.id+' '+(i.placeholder||'')+' '+(i.getAttribute('aria-label')||'')+' '+(i.autocomplete||'')).toLowerCase();if(k.includes('first')&&k.includes('name')){t(i,p.f);c++;}else if(k.includes('last')&&k.includes('name')){t(i,p.l);c++;}else if((k.includes('full')&&k.includes('name'))||(k.includes('name')&&!k.includes('user')&&!k.includes('company')&&!k.includes('file'))){t(i,p.n);c++;}else if(k.includes('email')||i.type==='email'){t(i,p.e);c++;}else if(k.includes('phone')||k.includes('mobile')||i.type==='tel'){t(i,p.p);c++;}else if(k.includes('linkedin')){t(i,p.li);c++;}else if(k.includes('github')||k.includes('git')){t(i,p.gh);c++;}else if(k.includes('portfolio')||k.includes('website')||k.includes('url')){t(i,p.w);c++;}else if(k.includes('city')||k.includes('location')||k.includes('address')){t(i,p.loc);c++;}else if(k.includes('notice')||k.includes('availability')||k.includes('start date')){t(i,p.np);c++;}else if((k.includes('authorized')||k.includes('eligibility')||k.includes('work auth'))&&i.tagName!=='SELECT'){t(i,p.wa);c++;}else if(i.tagName==='TEXTAREA'&&(k.includes('cover')||k.includes('pitch')||k.includes('note')||k.includes('summary'))){t(i,p.c);c++;}});document.querySelectorAll('input[type="radio"],input[type="checkbox"]').forEach(b=>{const txt=(b.parentElement?b.parentElement.innerText:'').toLowerCase();if(txt.includes('authorized')&&(txt.includes('yes')||b.value.toLowerCase()==='yes'||(p.wa&&p.wa.toLowerCase().includes('yes')))){b.checked=true;b.dispatchEvent(new Event('change',{bubbles:true}));c++;}if(txt.includes('sponsorship')&&(txt.includes('no')||b.value.toLowerCase()==='no')){b.checked=true;b.dispatchEvent(new Event('change',{bubbles:true}));c++;}});const toast=document.createElement('div');toast.innerText='JobHunt: Auto-filled '+c+' fields!';toast.style.cssText='position:fixed;top:20px;right:20px;background:#1f6feb;color:#fff;padding:12px 18px;border-radius:8px;font-family:sans-serif;font-size:13px;font-weight:600;z-index:999999;box-shadow:0 8px 24px rgba(0,0,0,0.5);';document.body.appendChild(toast);setTimeout(()=>toast.remove(),3500);})();`;
    }

    function updateBookmarkletCode(profile) {
      if (!profile) profile = getApplicantProfile();
      BOOKMARKLET_CODE = generateBookmarkletScript(profile);
      const link = document.getElementById('bookmarklet-drag-link');
      if (link) {
        link.href = BOOKMARKLET_CODE;
      }
    }

    function copyBookmarkletCode(btn) {
      if (!BOOKMARKLET_CODE) {
        updateBookmarkletCode();
      }
      copyFieldValue(BOOKMARKLET_CODE, btn);
      showToast('Bookmarklet code copied to clipboard! Paste as a browser bookmark URL.');
    }

    function loadAutofillForm(profile) {
      if (!profile) profile = getApplicantProfile();
      const map = {
        'autofill-first-name': profile.firstName,
        'autofill-last-name': profile.lastName,
        'autofill-full-name': profile.fullName,
        'autofill-email': profile.email,
        'autofill-phone': profile.phone,
        'autofill-location': profile.location,
        'autofill-linkedin': profile.linkedin,
        'autofill-github': profile.github,
        'autofill-portfolio': profile.portfolio,
        'autofill-notice-period': profile.noticePeriod,
        'autofill-work-auth': profile.workAuth,
        'autofill-summary': profile.summary
      };
      for (const [id, val] of Object.entries(map)) {
        const el = document.getElementById(id);
        if (el) el.value = val !== undefined ? val : '';
      }
    }

    function saveAutofillProfile() {
      const profile = {
        firstName: (document.getElementById('autofill-first-name')?.value || '').trim(),
        lastName: (document.getElementById('autofill-last-name')?.value || '').trim(),
        fullName: (document.getElementById('autofill-full-name')?.value || '').trim(),
        email: (document.getElementById('autofill-email')?.value || '').trim(),
        phone: (document.getElementById('autofill-phone')?.value || '').trim(),
        location: (document.getElementById('autofill-location')?.value || '').trim(),
        linkedin: (document.getElementById('autofill-linkedin')?.value || '').trim(),
        github: (document.getElementById('autofill-github')?.value || '').trim(),
        portfolio: (document.getElementById('autofill-portfolio')?.value || '').trim(),
        noticePeriod: (document.getElementById('autofill-notice-period')?.value || '').trim(),
        workAuth: (document.getElementById('autofill-work-auth')?.value || '').trim(),
        summary: (document.getElementById('autofill-summary')?.value || '').trim()
      };

      try {
        localStorage.setItem(AUTOFIL_STORAGE_KEY, JSON.stringify(profile));
      } catch (e) {
        console.error('Failed to save applicant profile to localStorage:', e);
      }

      updateBookmarkletCode(profile);
      showToast('Applicant profile saved! Bookmarklet link updated.');
    }

    function resetAutofillProfile() {
      try {
        localStorage.setItem(AUTOFIL_STORAGE_KEY, JSON.stringify(DEFAULT_APPLICANT_PROFILE));
      } catch (e) {
        console.error('Failed to reset applicant profile in localStorage:', e);
      }
      loadAutofillForm(DEFAULT_APPLICANT_PROFILE);
      updateBookmarkletCode(DEFAULT_APPLICANT_PROFILE);
      showToast('Applicant profile reset to defaults.');
    }

    function initBookmarkletLink() {
      const profile = getApplicantProfile();
      loadAutofillForm(profile);
      updateBookmarkletCode(profile);
    }

    let linkedInScrapeState = {
      is_running: false,
      status: 'idle',
      jobs_found: 0,
      jobs_added: 0,
      last_scan: null,
      error: null
    };

    let linkedInPollInterval = null;

    async function triggerLinkedInScrape(event) {
      if (event) {
        event.stopPropagation();
        if (event.preventDefault) event.preventDefault();
      }

      const isStaticOrHttps = window.location.protocol === 'https:' && !window.location.host.includes('localhost') && !window.location.host.includes('127.0.0.1');

      if (isStaticOrHttps) {
        showToast('Live scrapers run automatically in the cloud via GitHub Actions. Opening workflow actions...');
        window.open('https://github.com/shubhaammm08/Job-Hunt/actions', '_blank');
        return;
      }

      const btn = document.getElementById('btn-linkedin-scrape');
      if (btn) {
        btn.disabled = true;
        const span = btn.querySelector('span');
        if (span) span.innerText = 'Scraping...';
      }

      showToast('Initiating LinkedIn scrape...');

      try {
        const res = await fetch('/api/sources/linkedin/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });

        if (res.status === 409) {
          showToast('LinkedIn scrape is already in progress.');
          pollLinkedInStatus();
          return;
        }

        if (!res.ok) {
          if (res.status === 404 || isStaticOrHttps) {
            showToast('Local backend API unavailable. Start server via "python gui/server.py" to run scrapers.');
          } else {
            const errData = await res.json().catch(() => ({}));
            showToast('LinkedIn scrape error: ' + (errData.message || res.statusText));
          }
          if (btn) {
            btn.disabled = false;
            const span = btn.querySelector('span');
            if (span) span.innerText = 'Run Scrape';
          }
          return;
        }

        const data = await res.json();
        showToast(data.message || 'LinkedIn scrape started in background.');
        pollLinkedInStatus();
      } catch (err) {
        if (isStaticOrHttps || window.location.protocol === 'file:') {
          showToast('Live scraper requires local GUI server ("python gui/server.py").');
        } else {
          showToast('Network error connecting to backend API. Ensure server is running.');
        }
        if (btn) {
          btn.disabled = false;
          const span = btn.querySelector('span');
          if (span) span.innerText = 'Run Scrape';
        }
      }
    }

    async function pollLinkedInStatus() {
      if (linkedInPollInterval) {
        clearInterval(linkedInPollInterval);
        linkedInPollInterval = null;
      }

      const updateCardFromStatus = (st) => {
        linkedInScrapeState.is_running = !!st.is_running;
        linkedInScrapeState.status = st.status || 'idle';
        if (typeof st.jobs_found === 'number') linkedInScrapeState.jobs_found = st.jobs_found;
        if (typeof st.jobs_added === 'number') linkedInScrapeState.jobs_added = st.jobs_added;
        if (st.last_scan) linkedInScrapeState.last_scan = st.last_scan;
        if (st.error !== undefined) linkedInScrapeState.error = st.error;

        renderSources();
      };

      const checkStatus = async () => {
        try {
          const res = await fetch('/api/sources/linkedin/status');
          if (!res.ok) {
            if (linkedInPollInterval) clearInterval(linkedInPollInterval);
            linkedInPollInterval = null;
            return;
          }
          const st = await res.json();
          updateCardFromStatus(st);

          if (!st.is_running) {
            if (linkedInPollInterval) {
              clearInterval(linkedInPollInterval);
              linkedInPollInterval = null;
            }
            if (st.status === 'completed') {
              showToast(`LinkedIn scrape completed! ${st.jobs_found || 0} jobs found, ${st.jobs_added || 0} added.`);
              loadData();
            } else if (st.status === 'error') {
              showToast(`LinkedIn scrape error: ${st.error || 'Unknown error'}`);
            } else if (st.status === 'auth_required') {
              showToast('LinkedIn session expired or authentication required. Run "python -m jobhunt linkedin-auth".');
            }
          }
        } catch (e) {
          if (linkedInPollInterval) {
            clearInterval(linkedInPollInterval);
            linkedInPollInterval = null;
          }
        }
      };

      await checkStatus();
      if (linkedInScrapeState.is_running) {
        linkedInPollInterval = setInterval(checkStatus, 2500);
      }
    }

    async function fetchLinkedInStatus() {
      try {
        const res = await fetch('/api/sources/linkedin/status');
        if (res.ok) {
          const st = await res.json();
          linkedInScrapeState.is_running = !!st.is_running;
          linkedInScrapeState.status = st.status || 'idle';
          if (typeof st.jobs_found === 'number') linkedInScrapeState.jobs_found = st.jobs_found;
          if (typeof st.jobs_added === 'number') linkedInScrapeState.jobs_added = st.jobs_added;
          if (st.last_scan) linkedInScrapeState.last_scan = st.last_scan;
          if (st.error !== undefined) linkedInScrapeState.error = st.error;
          if (st.is_running && !linkedInPollInterval) {
            pollLinkedInStatus();
          }
          renderSources();
        }
      } catch (e) {}
    }

    let currentSourceFilter = 'active';

    function filterSources(category) {
      currentSourceFilter = category;
      document.querySelectorAll('[id^="source-chip-"]').forEach(btn => btn.classList.remove('active'));
      const activeBtn = document.getElementById('source-chip-' + category);
      if (activeBtn) activeBtn.classList.add('active');
      renderSources();
    }

    function renderSources() {
      const container = document.getElementById('sources-grid');
      if (!container) return;
      const allSources = (appData.source_health && appData.source_health.length) ? appData.source_health : (window.SOURCES_CATALOG || []);
      
      let sourcesList = [...allSources];
      const hasLinkedInScraper = sourcesList.some(s => s.source === 'LinkedIn' || s.source === 'LinkedIn Scraper');
      if (!hasLinkedInScraper) {
        sourcesList.unshift({
          source: 'LinkedIn',
          category: 'professional_network',
          tier: 2,
          status: 'HEALTHY',
          jobs_found: linkedInScrapeState.jobs_found || 0,
          new_jobs: linkedInScrapeState.jobs_added || 0,
          errors: linkedInScrapeState.error ? [linkedInScrapeState.error] : [],
          last_scan: linkedInScrapeState.last_scan || null
        });
      }

      let filtered = sourcesList;
      const activeNames = [
        'Greenhouse', 'Ashby', 'Lever', 'SmartRecruiters', 'Workable', 'Recruitee',
        'Personio', 'Breezy HR', 'BambooHR', 'Remotive', 'Remote OK',
        'Himalayas', 'Jobicy', 'Working Nomads', 'NoDesk', 'Hacker News Who Is Hiring',
        'LinkedIn', 'LinkedIn Scraper'
      ];
      if (currentSourceFilter === 'active') {
        filtered = sourcesList.filter(s => s.status === 'HEALTHY' || activeNames.includes(s.source));
      } else if (currentSourceFilter === 'direct_ats') {
        filtered = sourcesList.filter(s => s.category === 'direct_ats');
      } else if (currentSourceFilter === 'remote') {
        filtered = sourcesList.filter(s => s.category === 'remote' || s.category === 'startup');
      } else if (currentSourceFilter === 'india_job_board') {
        filtered = sourcesList.filter(s => s.category === 'india_job_board' || s.category === 'global_job_board' || s.category === 'professional_network' || s.source === 'LinkedIn' || s.source === 'LinkedIn Scraper');
      } else if (currentSourceFilter === 'fresher') {
        filtered = sourcesList.filter(s => s.category === 'fresher' || s.category === 'ai_specific');
      }

      if (!filtered.length) {
        container.innerHTML = '<div style="padding:20px;color:var(--text-muted);grid-column: 1 / -1;text-align:center;">No sources matching this category.</div>';
        return;
      }

      container.innerHTML = filtered.map(s => {
        const isHealthy = s.status === 'HEALTHY' || activeNames.includes(s.source);
        const dotClass = isHealthy ? 'status-healthy' : 'status-config';
        const isRapidApi = ['LinkedIn Jobs', 'LinkedIn Jobs India', 'Indeed', 'Indeed India', 'Naukri', 'Glassdoor', 'ZipRecruiter'].includes(s.source);
        const badgeClass = isHealthy ? 'badge-healthy' : 'badge-config';
        const statusLabel = isHealthy ? 'Active Feed' : (isRapidApi ? 'RapidAPI Ready' : 'Config Needed');

        if (s.source === 'LinkedIn' || s.source === 'LinkedIn Scraper') {
          const isRunning = !!linkedInScrapeState.is_running;
          let liBadgeClass = 'badge-healthy';
          let liStatusLabel = 'Active Scraper';
          if (isRunning) {
            liBadgeClass = 'badge-config';
            liStatusLabel = 'Running';
          } else if (linkedInScrapeState.status === 'auth_required' || s.status === 'CONFIG_REQUIRED') {
            liBadgeClass = 'badge-config';
            liStatusLabel = 'Config Needed';
          } else if (linkedInScrapeState.status === 'error') {
            liBadgeClass = 'badge-config';
            liStatusLabel = 'Error';
          }

          const jobsFound = linkedInScrapeState.jobs_found !== undefined ? linkedInScrapeState.jobs_found : (s.jobs_found || 0);
          const jobsAdded = linkedInScrapeState.jobs_added !== undefined ? linkedInScrapeState.jobs_added : (s.new_jobs || 0);
          const lastScan = linkedInScrapeState.last_scan || s.last_scan;
          let scanTimeStr = 'Never';
          if (lastScan) {
            try {
              const d = new Date(lastScan);
              scanTimeStr = isNaN(d.getTime()) ? String(lastScan).substring(0, 16) : d.toLocaleString();
            } catch (e) {
              scanTimeStr = String(lastScan).substring(0, 16);
            }
          }
          const errMsg = linkedInScrapeState.error || (s.errors && s.errors.length ? s.errors[0] : null);
          const errHtml = errMsg ? `<div style="font-size:11px;color:#f85149;margin-top:4px;">Error: ${escapeHtml(errMsg)}</div>` : '';

          return `
            <div class="source-card" id="source-card-linkedin">
              <div class="source-info" style="flex:1;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                  <h4 style="font-size:13.5px;font-weight:700;">${escapeHtml(s.source || 'LinkedIn')}</h4>
                  <span class="badge-pill ${liBadgeClass}" id="badge-linkedin-status">${liStatusLabel}</span>
                </div>
                <div style="font-size:11px;color:var(--text-muted);">
                  PROFESSIONAL NETWORK &bull; Tier 2
                </div>
                <div class="source-desc">Playwright Automated Scraper &middot; Keyword &amp; Location Queries</div>
                <div style="font-size:11.5px;color:var(--text-main);margin-top:6px;display:flex;flex-wrap:wrap;gap:8px;">
                  <span><strong>Jobs Found:</strong> ${jobsFound}</span>
                  <span><strong>Jobs Added:</strong> ${jobsAdded}</span>
                  <span><strong>Last Scan:</strong> ${escapeHtml(scanTimeStr)}</span>
                </div>
                ${errHtml}
                <div style="margin-top:10px;display:flex;align-items:center;gap:8px;">
                  <button class="btn-actions" onclick="triggerLinkedInScrape(event)" id="btn-linkedin-scrape" ${isRunning ? 'disabled' : ''}>
                    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                    <span>${isRunning ? 'Scraping...' : (window.location.protocol === 'https:' ? 'Cloud Scraper Status' : 'Run Scrape')}</span>
                  </button>
                </div>
              </div>
            </div>
          `;
        }

        let desc = 'Configured via companies.yaml or custom feed URL';
        if (s.source === 'Greenhouse') desc = '30+ Verified Companies · Open REST API';
        else if (s.source === 'Ashby') desc = 'Top AI Startups (OpenAI, Modal) · Open API';
        else if (s.source === 'Lever') desc = 'Spotify, Palantir · Open JSON Postings API';
        else if (s.source === 'SmartRecruiters') desc = 'Delivery Hero, CERN · Open Postings API';
        else if (s.source === 'Workable') desc = 'Skroutz, Startups · Open Widget API';
        else if (s.source === 'Personio') desc = 'Personio SE & European Tech · Open XML Feed';
        else if (s.source === 'Breezy HR') desc = 'Breezy HR & Tech Boards · Open JSON API';
        else if (s.source === 'BambooHR') desc = 'BambooHR Companies · Open Careers JSON';
        else if (s.source === 'Remotive') desc = 'Public Remote Engineering API';
        else if (s.source === 'Remote OK') desc = 'Daily Global Remote JSON Stream';
        else if (s.source === 'Himalayas') desc = 'Live Remote Engineering & Data RSS Feed';
        else if (s.source === 'Jobicy') desc = '100+ Live Tech & Dev Jobs · Public JSON API';
        else if (s.source === 'Working Nomads') desc = 'Curated Remote Engineering · Public API';
        else if (s.source === 'NoDesk') desc = 'Global Remote Digital Nomad · Public XML Feed';
        else if (s.source === 'Hacker News Who Is Hiring') desc = 'Monthly Who Is Hiring Thread Feed';
        else if (isRapidApi) desc = 'RapidAPI JSearch · Add RAPIDAPI_KEY to GitHub Secrets (500 free/mo)';
        else if (s.category === 'direct_ats') desc = 'Enterprise ATS · Add company CXS URL in config.yaml';
        else if (s.category === 'india_job_board') desc = 'Requires Partner API / Token (Anti-bot protected)';
        else if (s.category === 'global_job_board') desc = 'Requires Partner API / Token (Anti-bot protected)';
        else if (s.category === 'fresher') desc = 'Fresher Portal · Connect feed in config.yaml';
        else if (s.category === 'ai_specific') desc = 'AI Specialized · Connect feed in config.yaml';

        return `
          <div class="source-card">
            <div class="source-info" style="flex:1;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                <h4 style="font-size:13.5px;font-weight:700;">${escapeHtml(s.source || '')}</h4>
                <span class="badge-pill ${badgeClass}">${statusLabel}</span>
              </div>
              <div style="font-size:11px;color:var(--text-muted);">
                ${escapeHtml((s.category || 'Direct ATS').replace('_', ' ').toUpperCase())} &bull; Tier ${s.tier || 1}
              </div>
              <div class="source-desc">${escapeHtml(desc)}</div>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderProfile() {
      const p = appData.profile || {};
      if (p.name) document.getElementById('profile-name').innerText = p.name;
      if (p.current_title) document.getElementById('profile-title').innerText = p.current_title;
      if (document.getElementById('profile-email')) {
        const emailStr = p.email || 'ssk080204@gmail.com';
        const phoneStr = p.phone || '+918169832448';
        document.getElementById('profile-email').innerText = `${emailStr} · ${phoneStr}`;
      }
      
      const skillsContainer = document.getElementById('profile-skills');
      if (skillsContainer) {
        if (p.skills && typeof p.skills === 'object' && !Array.isArray(p.skills)) {
          let html = '';
          for (const [category, skillList] of Object.entries(p.skills)) {
            html += `<div style="width:100%;margin-top:6px;margin-bottom:3px;"><strong style="font-size:12px;color:var(--accent-blue);">${escapeHtml(category)}:</strong></div>`;
            html += `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">` + skillList.map(s => `<span class="tag" style="background:#1f242d;color:#79c0ff;">${escapeHtml(s)}</span>`).join('') + `</div>`;
          }
          skillsContainer.innerHTML = html;
        } else if (p.core_skills) {
          skillsContainer.innerHTML = p.core_skills.map(s => `<span class="tag" style="background:#1f242d;color:#79c0ff;">${escapeHtml(s)}</span>`).join('');
        }
      }

      const rolesContainer = document.getElementById('profile-target-roles');
      const targetTracks = p.target_roles || p.target_titles || [];
      if (rolesContainer && targetTracks.length) {
        rolesContainer.innerHTML = targetTracks.map(t => `<span class="tag tag-family">${escapeHtml(t)}</span>`).join('');
      }
    }

    function renderDigest() {
      const iframe = document.getElementById('digest-frame');
      if (!iframe) return;
      if (appData.digest_html) {
        iframe.srcdoc = appData.digest_html;
      } else {
        fetch('digest.html')
          .then(res => res.ok ? res.text() : null)
          .then(html => {
            if (html) {
              appData.digest_html = html;
              iframe.srcdoc = html;
            }
          })
          .catch(() => {});
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
          current_title: "AI & Software Engineer",
          email: "ssk080204@gmail.com",
          phone: "+918169832448",
          location: "Mumbai Metropolitan Region / Remote",
          target_roles: [
            "AI Engineer",
            "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)",
            "API Development / Backend Engineer (FastAPI, Flask, REST APIs)",
            "Full-Stack Developer / Engineer (React, Node.js)",
            "Mobile Developer (Flutter)",
            "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)",
            "Machine Learning & Python Developer"
          ],
          target_titles: [
            "AI Engineer",
            "GenAI & LLM Engineer / Developer (GenAI, LLMs, NLP, LangChain)",
            "API Development / Backend Engineer (FastAPI, Flask, REST APIs)",
            "Full-Stack Developer / Engineer (React, Node.js)",
            "Mobile Developer (Flutter)",
            "Automation Engineer (n8n, Docker, CI/CD, Workflow Automation)",
            "Machine Learning & Python Developer"
          ],
          skills: {
            "AI & ML": ["Machine Learning", "GenAI", "LLMs", "NLP", "LangChain", "Python"],
            "API & Backend": ["FastAPI", "Flask", "REST APIs", "Node.js", "Python"],
            "Full-Stack & Frontend": ["React", "Node.js"],
            "Mobile": ["Flutter"],
            "Automation & DevOps": ["n8n", "Docker", "CI/CD", "Automation"],
            "Data & BI": ["SQL", "Power BI", "Pandas", "NumPy", "Scikit-learn"]
          },
          core_skills: [
            "Machine Learning", "GenAI", "LLMs", "NLP", "LangChain", "Python",
            "FastAPI", "Flask", "REST APIs", "Node.js", "React", "Flutter",
            "n8n", "Docker", "CI/CD", "Automation", "SQL", "Power BI", "Pandas", "NumPy", "Scikit-learn"
          ]
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

    window.addEventListener('DOMContentLoaded', () => {
      initBookmarkletLink();
      loadData();
    });
  </script>
</body>
</html>
"""

def main():
    root = os.path.dirname(os.path.abspath(__file__))

    # Keep the repo-root avatar mirror in sync for branch-based GitHub Pages
    # deployments (which serve root index.html and expect ./avatars/).
    src_avatars = os.path.join(root, "gui", "avatars")
    dst_avatars = os.path.join(root, "avatars")
    if os.path.isdir(src_avatars):
        shutil.copytree(src_avatars, dst_avatars, dirs_exist_ok=True)

    gui_index = os.path.join(root, "gui", "index.html")
    if os.path.exists(gui_index):
        with open(gui_index, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = HTML_TEMPLATE
    print("Loaded gui/index.html responsive template.")

    # Bundle live data into root index.html
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
    catalog_path = os.path.join(root, "jobhunt", "sources_catalog.json")
    health_data = []
    if os.path.exists(health_path):
        try:
            with open(health_path, "r", encoding="utf-8") as f:
                health_data = json.load(f)
        except Exception:
            health_data = []
    if not health_data and os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                health_data = json.load(f)
        except Exception:
            health_data = []

    # Exclude disabled/paywalled sources from dashboard health payload
    forbidden_sources = {"we work remotely", "flexjobs"}
    health_data = [
        s for s in health_data
        if s.get("source", "").strip().lower() not in forbidden_sources
    ]

    has_linkedin = any(s.get("source") == "LinkedIn" for s in health_data)
    if not has_linkedin:
        li_status_path = os.path.join(root, "out", "linkedin_status.json")
        li_status = {}
        if os.path.exists(li_status_path):
            try:
                with open(li_status_path, "r", encoding="utf-8") as f:
                    li_status = json.load(f)
            except Exception:
                pass
        health_data.insert(0, {
            "source": "LinkedIn",
            "category": "professional_network",
            "tier": 2,
            "status": "HEALTHY",
            "jobs_found": li_status.get("jobs_found", 0),
            "jobs_after_filtering": li_status.get("jobs_found", 0),
            "new_jobs": li_status.get("jobs_added", 0),
            "duplicates_removed": li_status.get("duplicates_filtered", 0),
            "errors": [li_status["error"]] if li_status.get("error") else [],
            "last_scan": li_status.get("last_scan")
        })

    digest_html = ""
    for dp in [
        os.path.join(root, "out", "digest.html"),
        os.path.join(root, "digest.html"),
        os.path.join(root, "gui", "digest.html")
    ]:
        if os.path.exists(dp):
            try:
                with open(dp, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    digest_html = content
                    break
            except Exception:
                pass

    if digest_html:
        digest_html = digest_html.replace("🎯", "")
        for target_file in [os.path.join(root, "digest.html"), os.path.join(root, "gui", "digest.html")]:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(digest_html)

    jobs_list = []
    for k, v in seen_data.items():
        if isinstance(v, dict):
            entry = {"job_id": k, **v}
            k_str = str(k).lower()
            if k_str.startswith("linkedin") or str(entry.get("platform", "")).lower() == "linkedin":
                url_str = str(entry.get("url") or "")
                if not url_str or not url_str.startswith("https://www.linkedin.com/jobs/view/"):
                    m = re.search(r"(\d{6,})", k_str + " " + url_str)
                    if m:
                        entry["url"] = f"https://www.linkedin.com/jobs/view/{m.group(1)}"
            jobs_list.append(entry)
    jobs_list.sort(key=lambda j: (j.get("score") or 0.0, j.get("first_seen") or ""), reverse=True)

    payload = {
        "jobs": jobs_list,
        "stats": {
            "total": len(jobs_list),
            "applied": sum(1 for j in jobs_list if j.get("applied")),
            "emailed": sum(1 for j in jobs_list if j.get("emailed")),
            "recommended": sum(1 for j in jobs_list if (j.get("score") or 0.0) >= 6.0),
            "sources_count": len(health_data) or 86
        },
        "profile": profile_data,
        "source_health": health_data,
        "digest_html": digest_html
    }

    injected_data = f"<script>window.INITIAL_DATA = {json.dumps(payload, ensure_ascii=False)};</script>\n</head>"
    root_html_content = template.replace("</head>", injected_data, 1)

    if digest_html:
        escaped_srcdoc = digest_html.replace("&", "&amp;").replace('"', "&quot;")
        root_html_content = root_html_content.replace(
            '<iframe class="digest-frame" id="digest-frame" src="digest.html"></iframe>',
            f'<iframe class="digest-frame" id="digest-frame" src="digest.html" srcdoc="{escaped_srcdoc}"></iframe>'
        )
    root_index = os.path.join(root, "index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(root_html_content)
    print(f"Updated root index.html with {len(jobs_list)} jobs and mobile enhancements.")

if __name__ == "__main__":
    main()
