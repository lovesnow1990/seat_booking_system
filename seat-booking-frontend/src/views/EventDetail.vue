<template>
  <div class="event-detail-page">
    <div v-if="lockedSeatsByMe.length > 0" class="locked-warning">
      <p>您有尚未完成的座位鎖定，請選擇：</p>
      <button @click="unlockMySeats">解鎖所有座位</button>
      <span style="display: inline-block; width: 16px"></span>
      <button @click="goToCheckout">前往登記頁面</button>
    </div>
    <p v-if="loading">載入活動詳情中...</p>
    <p v-if="error" class="error-message">{{ error }}</p>

    <div v-if="event && !loading">
      <h1>{{ event.name }}</h1>
      <p>地點: {{ event.venue_name }}</p>
      <p>時間: {{ formattedEventTime }}</p>

      <h2>選擇您的座位</h2>
      <div class="seat-grid">
        <div v-for="row in seatRows" :key="row" class="seat-row">
          <div
            v-for="seat in seatsByRow[row]"
            :key="seat.id"
            :class="[
              'seat',
              seat.status,
              { 'is-selected': isSelected(seat) },
              {
                'locked-by-other':
                  seat.status === 'locked' &&
                  seat.locked_by_session !== sessionId,
              },
            ]"
            @click="toggleSeatSelection(seat)"
          >
            <div class="seat-number">{{ row }}{{ seat.column }}</div>
            <div class="seat-price">{{ seat.price }}</div>
          </div>
        </div>
      </div>

      <div class="summary">
        <h3>已選座位:</h3>
        <ul v-if="selectedSeats.length > 0">
          <li v-for="seat in selectedSeats" :key="seat.id">
            {{ seat.row }}{{ seat.column }} ({{ seat.price }} NTD)
            <button class="remove-seat" @click="removeSeat(seat.id)">X</button>
          </li>
        </ul>
        <p v-else>您還沒有選擇任何座位。</p>
        <h3>總金額: {{ totalAmount }} NTD</h3>

        <button
          :disabled="isLockingSeats || selectedSeats.length === 0"
          @click="proceedToCheckout"
        >
          {{ isLockingSeats ? "鎖定座位中..." : "前往登記" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import apiClient from "@/api"; // 引入 apiClient 實例
import { v4 as uuidv4 } from "uuid"; // 用於生成唯一的 session ID
import axios from "axios"; // 引入 axios 以便檢查錯誤類型

export default {
  name: "EventDetail",
  props: ["id"], // 從路由接收 event ID
  data() {
    return {
      event: null,
      seats: [],
      selectedSeats: [],
      totalAmount: 0,
      loading: true,
      error: null,
      isLockingSeats: false,
      sessionId: null, // 用於識別當前用戶會話的唯一 ID
      lockedSeatsByMe: [], // 自己鎖定但未完成的座位
    };
  },
  computed: {
    // 格式化活動時間
    formattedEventTime() {
      if (this.event && this.event.event_date && this.event.event_time) {
        // 組合成 'YYYY-MM-DDTHH:mm:ss'
        const dateTimeStr = `${this.event.event_date}T${this.event.event_time}`;
        const options = {
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        };
        return new Date(dateTimeStr).toLocaleString("zh-TW", options);
      }
      return "";
    },
    // 將座位按排分組
    seatsByRow() {
      const grouped = {};
      this.seats.forEach((seat) => {
        if (!grouped[seat.row]) {
          grouped[seat.row] = [];
        }
        grouped[seat.row].push(seat);
      });
      // 對每排的座位按 column 排序
      for (const row in grouped) {
        grouped[row].sort((a, b) => {
          // 假設 column 是數字或可比較字串，使用 localeCompare 進行自然排序
          return a.column.localeCompare(b.column, undefined, { numeric: true });
        });
      }
      return grouped;
    },
    // 獲取所有座位排的唯一字母 (A, B, C...)
    seatRows() {
      // 確保座位行按字母順序排序
      return Object.keys(this.seatsByRow).sort();
    },
  },
  async created() {
    // 檢查是否有存儲的 sessionId，沒有則生成一個新的
    let storedSessionId = localStorage.getItem("session_id");
    if (!storedSessionId) {
      storedSessionId = uuidv4();
      localStorage.setItem("session_id", storedSessionId);
    }
    this.sessionId = storedSessionId;

    await this.fetchEventAndSeats();
    await this.checkMyLockedSeats();
  },
  methods: {
    async fetchEventAndSeats() {
      this.loading = true;
      this.error = null;
      try {
        const eventResponse = await apiClient.get(`/api/events/${this.id}/`);
        this.event = eventResponse.data;

        const seatsResponse = await apiClient.get(
          `/api/events/${this.id}/seats/`
        );
        this.seats = seatsResponse.data;

        // 在重新獲取座位資訊後，檢查之前選中的座位是否仍然可用或由當前會話鎖定
        this.selectedSeats = this.selectedSeats.filter((selectedSeat) => {
          const currentSeatState = this.seats.find(
            (s) => s.id === selectedSeat.id
          );
          return (
            currentSeatState &&
            (currentSeatState.status === "available" ||
              (currentSeatState.status === "locked" &&
                currentSeatState.locked_by_session === this.sessionId))
          );
        });
        this.calculateTotal();
        // 重新檢查自己鎖定的座位
        await this.checkMyLockedSeats();
      } catch (err) {
        this.error = "載入活動信息失敗！";
        if (
          axios.isAxiosError(err) &&
          err.response &&
          err.response.data &&
          err.response.data.message
        ) {
          this.error = err.response.data.message;
        }
        console.error("Error fetching event or seats:", err);
      } finally {
        this.loading = false;
      }
    },
    async checkMyLockedSeats() {
      try {
        const response = await apiClient.get(
          `/api/events/${this.id}/seats/?session_id=${this.sessionId}&status=locked_by_session`
        );
        this.lockedSeatsByMe = response.data.filter(
          (seat) =>
            seat.status === "locked" &&
            seat.locked_by_session === this.sessionId
        );
      } catch (err) {
        this.lockedSeatsByMe = [];
      }
    },
    async unlockMySeats() {
      if (this.lockedSeatsByMe.length === 0) return;
      const seatIds = this.lockedSeatsByMe.map((seat) => seat.id);
      try {
        await apiClient.post("/api/seats/unlock/", {
          seat_ids: seatIds,
          session_id: this.sessionId,
        });
        this.lockedSeatsByMe = [];
        await this.fetchEventAndSeats();
      } catch (err) {
        alert("解鎖失敗，請稍後再試");
      }
    },
    goToCheckout() {
      this.$router.push({
        name: "SeatCheckout",
        params: {
          eventId: this.id,
          sessionId: this.sessionId,
        },
      });
    },
    // 判斷座位是否已被選中
    isSelected(seat) {
      return this.selectedSeats.some((s) => s.id === seat.id);
    },
    // 切換座位選擇狀態
    toggleSeatSelection(seat) {
      if (seat.status === "available") {
        const index = this.selectedSeats.findIndex((s) => s.id === seat.id);
        if (index > -1) {
          // 已選中，則移除
          this.selectedSeats.splice(index, 1);
        } else {
          // 未選中，則添加
          this.selectedSeats.push(seat);
        }
        this.calculateTotal();
      } else if (seat.status === "locked") {
        if (seat.locked_by_session === this.sessionId) {
          // 允許解除自己鎖定的座位 (如果業務邏輯允許)
          const index = this.selectedSeats.findIndex((s) => s.id === seat.id);
          if (index > -1) {
            this.selectedSeats.splice(index, 1);
            this.calculateTotal();
          }
        } else {
          alert("該座位已被其他用戶鎖定，請選擇其他座位。");
        }
      } else if (seat.status === "registered") {
        alert("該座位已被預訂，請選擇其他座位。");
      }
    },
    // 移除已選座位
    removeSeat(seatId) {
      this.selectedSeats = this.selectedSeats.filter((s) => s.id !== seatId);
      this.calculateTotal();
    },
    // 計算總金額
    calculateTotal() {
      this.totalAmount = this.selectedSeats.reduce(
        (sum, seat) => sum + parseFloat(seat.price),
        0
      );
    },
    async proceedToCheckout() {
      if (this.selectedSeats.length === 0) {
        alert("請先選擇座位！");
        return;
      }

      this.isLockingSeats = true;
      this.error = null;

      try {
        const seatIdsToLock = this.selectedSeats.map((s) => s.id);

        // **第一步：向後端發送請求鎖定座位**
        const lockResponse = await apiClient.post(`/api/seats/lock/`, {
          seat_ids: seatIdsToLock,
          session_id: this.sessionId, // 傳送當前使用者的 session_id
        });

        if (lockResponse.status === 200) {
          console.log("Seats locked successfully:", lockResponse.data);
          // **鎖定成功後，導航到結帳頁面，只傳遞 ID**
          this.$router.push({
            name: "SeatCheckout",
            query: {
              eventId: this.id, // 活動 ID
              sessionId: this.sessionId, // 會話 ID，讓結帳頁面可以憑此查詢鎖定的座位
            },
          });
        }
      } catch (err) {
        this.error = "鎖定座位失敗，請檢查座位狀態或稍後再試。";
        // 使用 axios.isAxiosError 判斷是否為 Axios 錯誤
        if (
          axios.isAxiosError(err) &&
          err.response &&
          err.response.data &&
          err.response.data.message
        ) {
          this.error = err.response.data.message;
          if (err.response.data.details) {
            for (const key in err.response.data.details) {
              if (Object.hasOwnProperty.call(err.response.data.details, key)) {
                this.error += ` ${key}: ${err.response.data.details[key].join(
                  "; "
                )}`;
              }
            }
          }
        }
        console.error("Error locking seats:", err);
        // 如果鎖定失敗，重新獲取座位狀態以更新 UI，並清空已選座位
        await this.fetchEventAndSeats();
        this.selectedSeats = [];
        this.calculateTotal();
      } finally {
        this.isLockingSeats = false;
      }
    },
  },
};
</script>

<style scoped>
.event-detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  text-align: center;
  font-family: "Arial", sans-serif;
  color: #333;
}

h1 {
  font-size: 2.5em;
  margin-bottom: 10px;
  color: #2c3e50;
}

h2 {
  font-size: 1.8em;
  margin-top: 30px;
  margin-bottom: 20px;
  color: #34495e;
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
}

h3 {
  font-size: 1.5em;
  margin-top: 20px;
  margin-bottom: 10px;
  color: #34495e;
}

p {
  font-size: 1.1em;
  line-height: 1.6;
  margin-bottom: 10px;
}

.error-message {
  color: red;
  background-color: #ffe0e0;
  border: 1px solid red;
  padding: 10px;
  margin-bottom: 20px;
  border-radius: 5px;
  font-weight: bold;
}

.seat-grid {
  display: flex;
  flex-direction: column; /* 讓行排垂直堆疊 */
  align-items: center; /* 讓整個座位網格居中 */
  margin-top: 30px;
  padding: 20px;
  background-color: #fcfcfc;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.seat-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap; /* 允許座位在小螢幕上換行 */
  justify-content: center; /* 行內座位居中 */
}

.row-label {
  font-weight: bold;
  margin-right: 15px;
  min-width: 30px; /* 確保標籤有足夠空間 */
  text-align: right;
  font-size: 1.1em;
  color: #555;
}

.seat {
  width: 60px; /* 增加寬度 */
  height: 60px; /* 增加高度 */
  background-color: #e0e0e0;
  border: 1px solid #ccc;
  border-radius: 8px;
  margin: 6px;
  display: flex;
  flex-direction: column; /* 讓編號和價格上下排列 */
  justify-content: center; /* 垂直居中 */
  align-items: center; /* 水平居中 */
  font-weight: bold;
  cursor: pointer;
  position: relative; /* 用於定位價格 */
  transition: all 0.25s ease-in-out;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  font-size: 1.1em; /* 座位編號字體 */
  color: #444;
  line-height: 1.2; /* 調整行高 */
}

.seat-number {
  /* 負責顯示 A1, A2 這種編號 */
  font-size: 1em; /* 相對於父元素 (.seat) 的字體大小 */
  margin-bottom: 2px; /* 與價格的間距 */
}

.seat-price {
  /* 負責顯示金額 */
  font-size: 0.75em; /* 較小的字體大小 */
  color: #666;
  white-space: nowrap; /* 防止價格換行 */
}

/* 座位狀態樣式 */
.seat.available {
  background-color: #d4edda; /* 柔和的淺綠 */
  cursor: pointer;
  border-color: #88c99f;
}

.seat.available:hover {
  background-color: #a8e6cf; /* 較深的淺綠 */
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
}

.seat.locked {
  background-color: #ffe0b2; /* 柔和的淺橘黃 (鎖定中) */
  cursor: not-allowed;
  opacity: 0.9;
  border-color: #ffcc80;
}

.seat.locked-by-other {
  background-color: #ffcdd2; /* 柔和的淺紅 (被其他用戶鎖定) */
  cursor: not-allowed;
  opacity: 0.8;
  border-color: #ef9a9a;
}

.seat.registered {
  background-color: #eceff1; /* 柔和的淺灰 (已預訂) */
  cursor: not-allowed;
  opacity: 0.7;
  border-color: #b0bec5;
}

.seat.is-selected {
  background-color: #4caf50; /* 更醒目的綠色 */
  color: white;
  border-color: #388e3c;
  transform: scale(1.1); /* 放大選中的座位 */
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
  z-index: 1; /* 確保選中的座位在上方 */
}

.summary {
  margin-top: 40px;
  padding: 25px;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background-color: #f9f9f9;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  text-align: left; /* 讓列表內容靠左 */
}

.summary ul {
  list-style: none;
  padding: 0;
  margin-bottom: 20px;
}

.summary li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #e0e0e0;
  font-size: 1.1em;
  color: #555;
}

.summary li:last-child {
  border-bottom: none;
}

.remove-seat {
  background-color: #f44336; /* 紅色 */
  color: white;
  border: none;
  border-radius: 50%;
  width: 25px;
  height: 25px;
  font-size: 0.9em;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: background-color 0.2s ease, transform 0.1s ease;
  flex-shrink: 0; /* 防止按鈕被壓縮 */
  margin-left: 10px;
}

.remove-seat:hover {
  background-color: #d32f2f;
  transform: scale(1.1);
}

button {
  background-color: #4caf50; /* 綠色 */
  color: white;
  padding: 15px 30px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.2em;
  font-weight: bold;
  margin-top: 25px;
  transition: background-color 0.25s ease, transform 0.1s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

button:hover:not(:disabled) {
  background-color: #388e3c;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

button:disabled {
  background-color: #bdbdbd; /* 灰色 */
  cursor: not-allowed;
  opacity: 0.7;
  box-shadow: none;
}
</style>
