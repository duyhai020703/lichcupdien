// State
let state = {
  selectedDate: "",
  selectedUnit: "ALL",
  selectedWard: "ALL",
  searchKeyword: "",
  filterKp2Only: false,
  rawItems: [],
  wardsSummary: {},
  loading: false,
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

  // 1. Lọc nhanh: Chỉ hiển thị Khu phố 2, Phường Tân Ninh
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

  // 3. Gom nhóm theo Phường / Xã (Chuẩn theo format web lịch cúp điện)
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

  // Sắp xếp: Phường Tân Ninh lên đầu nếu có
  wardNames.sort((a, b) => {
    if (a.toLowerCase().includes("tân ninh")) return -1;
    if (b.toLowerCase().includes("tân ninh")) return 1;
    return a.localeCompare(b, "vi");
  });

  // Render từng bảng thẻ phường
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

  // Nút gửi Telegram
  const btnSendTg = document.getElementById("btnSendTelegram");
  if (btnSendTg) {
    btnSendTg.addEventListener("click", async () => {
      btnSendTg.disabled = true;
      btnSendTg.innerHTML = "⏳ Đang gửi Telegram...";
      try {
        const resp = await fetch("/api/send-weekly", { method: "POST" });
        const res = await resp.json();
        alert("✅ Đã gửi bản tin tổng hợp tới Telegram của bạn!");
      } catch (e) {
        alert("❌ Lỗi khi gửi Telegram: " + e.message);
      } finally {
        btnSendTg.disabled = false;
        btnSendTg.innerHTML = "📩 Gửi lịch cả tuần về Telegram";
      }
    });
  }

  // Load ban đầu
  loadData();
});
