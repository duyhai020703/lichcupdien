// State
let state = {
  currentView: "daily", // "daily" hoặc "weekly"
  selectedDate: "",
  selectedUnit: "ALL",
  selectedWard: "ALL",
  searchKeyword: "",
  filterKp2Only: false,
  rawItems: [],
  wardsSummary: {},
  loading: false,
  weeklyData: null,
};

// Utilities
function formatDateIso(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDateDisplay(d) {
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}`;
}

const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function initDateRow() {
  const row = document.getElementById("dateScrollRow");
  if (!row) return;
  row.innerHTML = "";
  const today = new Date();

  for (let i = 0; i < 7; i++) {
    const cur = new Date();
    cur.setDate(today.getDate() + i);
    const iso = formatDateIso(cur);
    const dayDisplay = formatDateDisplay(cur);

    let title = "";
    if (i === 0) title = "Hôm nay";
    else if (i === 1) title = "Ngày mai";
    else title = WEEKDAYS[cur.getDay()];

    const pill = document.createElement("div");
    pill.className = `date-pill ${i === 0 ? "active" : ""}`;
    pill.dataset.date = iso;
    pill.innerHTML = `
      <span class="day-title">${title}</span>
      <span class="day-sub">${dayDisplay}</span>
    `;

    pill.addEventListener("click", () => {
      document.querySelectorAll(".date-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.selectedDate = iso;
      state.selectedWard = "ALL";
      loadData();
    });

    row.appendChild(pill);
  }

  state.selectedDate = formatDateIso(today);
}

// Chuyển đổi giữa 2 chế độ xem: Lịch theo ngày vs Bảng tổng quan cả tuần
function switchView(viewMode) {
  state.currentView = viewMode;
  const tabDaily = document.getElementById("tabDaily");
  const tabWeekly = document.getElementById("tabWeekly");
  const dailyView = document.getElementById("dailyView");
  const weeklyView = document.getElementById("weeklyView");

  if (viewMode === "weekly") {
    tabDaily.classList.remove("active");
    tabWeekly.classList.add("active");
    dailyView.style.display = "none";
    weeklyView.style.display = "block";
    loadWeeklyData();
  } else {
    tabWeekly.classList.remove("active");
    tabDaily.classList.add("active");
    weeklyView.style.display = "none";
    dailyView.style.display = "block";
  }
}

// Tải bảng tổng quan cả tuần (T2 - CN)
async function loadWeeklyData() {
  const rowsList = document.getElementById("weeklyRowsList");
  const titleEl = document.getElementById("weeklyTitle");
  const btnRefreshWeekly = document.getElementById("btnRefreshWeekly");

  if (btnRefreshWeekly) btnRefreshWeekly.classList.add("rotating");

  rowsList.innerHTML = `
    <div style="text-align:center; padding: 40px 0;">
      <div class="spinner"></div>
      <p style="margin-top:12px; color: var(--text-secondary); font-size: 13px;">Đang quét lịch cả tuần từ EVN SPC...</p>
    </div>
  `;

  try {
    const resp = await fetch("/api/weekly");
    const data = await resp.json();
    state.weeklyData = data;

    // Cập nhật tiêu đề khoảng ngày
    const sDate = data.start_week ? data.start_week.split("-").reverse().join("/") : "";
    const eDate = data.end_week ? data.end_week.split("-").reverse().join("/") : "";
    if (sDate && eDate) {
      titleEl.textContent = `⚡ Bảng tổng quan cả tuần (${sDate.substring(0, 5)} - ${eDate})`;
    }

    renderWeeklyTable(data);
  } catch (err) {
    console.error(err);
    rowsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3>Không thể tải bảng tổng quan tuần</h3>
        <p>Vui lòng thử lại sau.</p>
      </div>
    `;
  } finally {
    if (btnRefreshWeekly) btnRefreshWeekly.classList.remove("rotating");
  }
}

// Render từng ngày trong bảng tổng quan tuần
function renderWeeklyTable(data) {
  const rowsList = document.getElementById("weeklyRowsList");
  const days = data.days || [];

  if (days.length === 0) {
    rowsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🟢</div>
        <h3>Không có lịch cúp điện tuần này</h3>
        <p>Toàn bộ các ngày trong tuần đều có điện ổn định.</p>
      </div>
    `;
    return;
  }

  rowsList.innerHTML = days.map(d => {
    const isOutage = d.is_outage;
    const badgeClass = isOutage ? "badge-red" : "badge-green";
    const indicatorClass = isOutage ? "indicator-red" : "indicator-green";
    const textClass = isOutage ? "text-red" : "text-green";
    const rowClass = isOutage ? "weekly-day-row has-outage" : "weekly-day-row no-outage";

    // Format ngày hiển thị: DD/MM
    const dateParts = d.date.split("-");
    const displayDate = dateParts.length === 3 ? `${dateParts[2]}/${dateParts[1]}` : d.date;

    const detailsHtml = (d.outages && d.outages.length > 0) ? `
      <div class="outage-details-mini">
        ${d.outages.map(o => `
          <div class="mini-detail-row">📍 <strong>Địa điểm:</strong> ${o.location}</div>
          <div class="mini-detail-row cause">🛠 <strong>Lý do:</strong> ${o.cause}</div>
        `).join("")}
      </div>
    ` : "";

    return `
      <div class="${rowClass}">
        <div class="day-badge-col">
          <span class="day-code-badge ${badgeClass}">${d.weekday_code}</span>
          <span class="day-date-sub">${displayDate}</span>
        </div>
        <div class="day-content-col">
          <div class="day-status-line">
            <span class="status-indicator ${indicatorClass}"></span>
            <strong class="${textClass}">${d.status_text}</strong>
          </div>
          ${detailsHtml}
        </div>
      </div>
    `;
  }).join("");
}

// Tải dữ liệu theo ngày
async function loadData() {
  const listEl = document.getElementById("outageList");
  const refreshBtn = document.getElementById("btnRefresh");

  state.loading = true;
  if (refreshBtn) refreshBtn.classList.add("rotating");

  listEl.innerHTML = `
    <div style="text-align:center; padding: 40px 0;">
      <div class="spinner"></div>
      <p style="margin-top:12px; color: var(--text-secondary); font-size: 13px;">Đang tải lịch từ EVN SPC...</p>
    </div>
  `;

  try {
    const url = `/api/tay-ninh-outages?date=${state.selectedDate}&unit=${state.selectedUnit}`;
    const resp = await fetch(url);
    const data = await resp.json();

    state.rawItems = data.items || [];
    state.wardsSummary = data.wards_summary || {};

    renderWardsNav();
    applyFiltersAndRender();
  } catch (err) {
    console.error(err);
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3>Không thể tải dữ liệu</h3>
        <p>Vui lòng kiểm tra lại kết nối mạng hoặc thử lại sau.</p>
      </div>
    `;
  } finally {
    state.loading = false;
    if (refreshBtn) refreshBtn.classList.remove("rotating");
  }
}

function renderWardsNav() {
  const nav = document.getElementById("wardNav");
  if (!nav) return;
  nav.innerHTML = "";

  const allChip = document.createElement("div");
  allChip.className = `ward-chip ${state.selectedWard === "ALL" ? "active" : ""}`;
  allChip.innerHTML = `Tất cả <span class="num">${state.rawItems.length}</span>`;
  allChip.addEventListener("click", () => {
    state.selectedWard = "ALL";
    renderWardsNav();
    applyFiltersAndRender();
  });
  nav.appendChild(allChip);

  Object.entries(state.wardsSummary).forEach(([wardName, count]) => {
    const chip = document.createElement("div");
    chip.className = `ward-chip ${state.selectedWard === wardName ? "active" : ""}`;
    chip.innerHTML = `${wardName} <span class="num">${count}</span>`;
    chip.addEventListener("click", () => {
      state.selectedWard = wardName;
      renderWardsNav();
      applyFiltersAndRender();
    });
    nav.appendChild(chip);
  });
}

function applyFiltersAndRender() {
  const listEl = document.getElementById("outageList");
  const summaryCountEl = document.getElementById("summaryCount");
  const summaryDescEl = document.getElementById("summaryDesc");

  let filtered = [...state.rawItems];

  // 1. Lọc nhanh KP2 Tân Ninh
  if (state.filterKp2Only) {
    filtered = filtered.filter(item => {
      const loc = item.location.toLowerCase();
      const isWard = loc.includes("tân ninh");
      const isKp2 = /\b(khu\s*ph[ốo]|kp)\.?\s*2\b/i.test(loc) || /\b(?:khu\s*ph[ốo]|kp)[^.;,]*\b2\b/i.test(loc);
      return isWard && isKp2;
    });
  }

  // 2. Lọc theo từ khóa tìm kiếm
  if (state.searchKeyword.trim() !== "") {
    const kw = state.searchKeyword.toLowerCase().trim();
    filtered = filtered.filter(item =>
      item.location.toLowerCase().includes(kw) ||
      item.cause.toLowerCase().includes(kw) ||
      (item.unit_name && item.unit_name.toLowerCase().includes(kw))
    );
  }

  // Cập nhật thẻ tổng quan
  summaryCountEl.textContent = `${filtered.length} điểm`;
  if (filtered.length === 0) {
    summaryCountEl.className = "badge-count green";
    summaryDescEl.textContent = "Không có khu vực nào cúp điện theo bộ lọc";
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🟢</div>
        <h3>Không có lịch cúp điện</h3>
        <p>Khu vực này hiện không có kế hoạch cúp điện trong ngày đã chọn.</p>
      </div>
    `;
    return;
  } else {
    summaryCountEl.className = "badge-count";
    summaryDescEl.textContent = `Có ${filtered.length} điểm ngừng cấp điện tại Tây Ninh`;
  }

  // 3. Gom nhóm theo Phường / Xã
  const wardGroups = {};
  filtered.forEach(item => {
    const wards = (item.wards && item.wards.length > 0) ? item.wards : ["Khu vực khác"];
    wards.forEach(w => {
      if (state.selectedWard !== "ALL" && w !== state.selectedWard) return;
      if (!wardGroups[w]) {
        wardGroups[w] = [];
      }
      if (!wardGroups[w].some(x => x.start_time === item.start_time && x.location === item.location)) {
        wardGroups[w].push(item);
      }
    });
  });

  const wardNames = Object.keys(wardGroups);
  if (wardNames.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🟢</div>
        <h3>Không có lịch cúp điện</h3>
        <p>Không tìm thấy địa điểm phù hợp với bộ lọc.</p>
      </div>
    `;
    return;
  }

  wardNames.sort((a, b) => {
    if (a.toLowerCase().includes("tân ninh")) return -1;
    if (b.toLowerCase().includes("tân ninh")) return 1;
    return a.localeCompare(b, "vi");
  });

  listEl.innerHTML = wardNames.map(wardName => {
    const items = wardGroups[wardName];
    items.sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));

    const isHighlightCard = items.some(item => {
      const loc = item.location.toLowerCase();
      return loc.includes("tân ninh") && (/\b(khu\s*ph[ốo]|kp)\.?\s*2\b/i.test(loc) || /\b(?:khu\s*ph[ốo]|kp)[^.;,]*\b2\b/i.test(loc));
    });

    const rowsHtml = items.map(item => {
      const locLower = item.location.toLowerCase();
      const isTargetKp2 = locLower.includes("tân ninh") && (/\b(khu\s*ph[ốo]|kp)\.?\s*2\b/i.test(locLower) || /\b(?:khu\s*ph[ốo]|kp)[^.;,]*\b2\b/i.test(locLower));
      const rowClass = isTargetKp2 ? "row-highlight" : "";

      return `
        <tr class="${rowClass}">
          <td class="col-time">${item.start_time || "--:--"}</td>
          <td class="col-time">${item.end_time || "--:--"}</td>
          <td class="col-location">
            <div class="location-main">${item.location}</div>
            <div class="location-unit">${item.unit_name || "ĐIỆN LỰC TÂY NINH"}</div>
          </td>
          <td class="col-cause">${item.cause || "Bảo trì, sửa chữa lưới điện"}</td>
        </tr>
      `;
    }).join("");

    return `
      <div class="ward-table-card ${isHighlightCard ? "highlight" : ""}">
        <div class="ward-header">
          <h3>Lịch cúp điện ${wardName}</h3>
          <span class="count-badge">${items.length} điểm</span>
        </div>
        <div class="table-responsive">
          <table class="outage-table">
            <thead>
              <tr>
                <th class="col-st">Thời gian bắt đầu</th>
                <th class="col-et">Thời gian kết thúc</th>
                <th>Địa điểm ngừng cung cấp điện</th>
                <th>Lý do</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join("");
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  initDateRow();

  // Tab chuyển đổi
  const tabDaily = document.getElementById("tabDaily");
  const tabWeekly = document.getElementById("tabWeekly");
  if (tabDaily) tabDaily.addEventListener("click", () => switchView("daily"));
  if (tabWeekly) tabWeekly.addEventListener("click", () => switchView("weekly"));

  // Nút nhanh "Xem bảng cả tuần" trong banner
  const btnQuickWeekly = document.getElementById("btnQuickWeekly");
  if (btnQuickWeekly) btnQuickWeekly.addEventListener("click", () => switchView("weekly"));

  // Nút làm mới bảng tuần
  const btnRefreshWeekly = document.getElementById("btnRefreshWeekly");
  if (btnRefreshWeekly) btnRefreshWeekly.addEventListener("click", () => loadWeeklyData());

  // Nút sao chép bảng tuần
  const btnCopyWeekly = document.getElementById("btnCopyWeekly");
  if (btnCopyWeekly) {
    btnCopyWeekly.addEventListener("click", () => {
      if (!state.weeklyData) return;
      const textToCopy = state.weeklyData.formatted_text
        .replace(/<[^>]+>/g, ""); // Xóa thẻ HTML tag
      navigator.clipboard.writeText(textToCopy).then(() => {
        alert("📋 Đã sao chép bảng tổng quan tuần vào bộ nhớ tạm! Bạn có thể dán vào Zalo/Facebook.");
      }).catch(err => {
        alert("Lỗi khi sao chép: " + err);
      });
    });
  }

  // Nút gửi Telegram từ bảng tuần
  const btnSendWeeklyFromView = document.getElementById("btnSendWeeklyFromView");
  if (btnSendWeeklyFromView) {
    btnSendWeeklyFromView.addEventListener("click", async () => {
      btnSendWeeklyFromView.disabled = true;
      btnSendWeeklyFromView.innerHTML = "⏳ Đang gửi Telegram...";
      try {
        const resp = await fetch("/api/send-weekly", { method: "POST" });
        await resp.json();
        alert("✅ Đã gửi bảng tổng quan tuần vào Group Telegram!");
      } catch (e) {
        alert("❌ Lỗi khi gửi Telegram: " + e.message);
      } finally {
        btnSendWeeklyFromView.disabled = false;
        btnSendWeeklyFromView.innerHTML = "📩 Gửi vào Group Telegram";
      }
    });
  }

  // Nút Lọc nhanh KP2 Tân Ninh
  const btnKp2 = document.getElementById("btnFilterKp2");
  if (btnKp2) {
    btnKp2.addEventListener("click", () => {
      state.filterKp2Only = !state.filterKp2Only;
      btnKp2.classList.toggle("active", state.filterKp2Only);
      applyFiltersAndRender();
    });
  }

  // Đổi đơn vị điện lực
  const selectUnit = document.getElementById("selectUnit");
  if (selectUnit) {
    selectUnit.addEventListener("change", (e) => {
      state.selectedUnit = e.target.value;
      state.selectedWard = "ALL";
      loadData();
    });
  }

  // Tìm kiếm
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchKeyword = e.target.value;
      applyFiltersAndRender();
    });
  }

  // Nút Refresh
  const btnRefresh = document.getElementById("btnRefresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      loadData();
    });
  }

  // Nút gửi Telegram ở thanh đáy
  const btnSendTg = document.getElementById("btnSendTelegram");
  if (btnSendTg) {
    btnSendTg.addEventListener("click", async () => {
      btnSendTg.disabled = true;
      btnSendTg.innerHTML = "⏳ Đang gửi Telegram...";
      try {
        const resp = await fetch("/api/send-weekly", { method: "POST" });
        await resp.json();
        alert("✅ Đã gửi bản tin tổng hợp tới Telegram của bạn!");
      } catch (e) {
        alert("❌ Lỗi khi gửi Telegram: " + e.message);
      } finally {
        btnSendTg.disabled = false;
        btnSendTg.innerHTML = "📩 Gửi lịch cả tuần về Telegram";
      }
    });
  }

  // Load dữ liệu ban đầu
  loadData();
});
