<template>
  <div class="checkout-page">
    <h1>確認訂單</h1>
    <p v-if="loading">載入中...</p>
    <p v-if="error" class="error-message">{{ error }}</p>

    <div
      v-if="!loading && parsedSelectedSeats && parsedSelectedSeats.length > 0"
    >
      <h2>已選座位</h2>
      <ul>
        <li v-for="seat in parsedSelectedSeats" :key="seat.id">
          {{ seat.row }}{{ seat.column }} ({{ seat.price }} NTD)
        </li>
      </ul>
      <h3>總金額: {{ parsedTotalAmount }} NTD</h3>
    </div>
    <p
      v-else-if="
        !loading && (!parsedSelectedSeats || parsedSelectedSeats.length === 0)
      "
    >
      沒有選中的座位信息，請返回活動頁面重新選擇。
    </p>

    <div
      v-if="!loading && parsedSelectedSeats && parsedSelectedSeats.length > 0"
      class="buyer-info-form"
    >
      <h2>登記資訊</h2>
      <form @submit.prevent="createOrder">
        <div class="form-group">
          <label for="buyerName">姓名:</label>
          <input id="buyerName" v-model="buyerName" type="text" required />
        </div>
        <button :disabled="isCreatingOrder" type="submit">
          {{ isCreatingOrder ? "建立訂單中..." : "確認登記" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import apiClient from "@/api"; // 引入 apiClient 實例
import axios from "axios"; // 引入 axios 以檢查錯誤類型

export default {
  name: "SeatCheckout", // 確保這個名稱與 src/router/index.js 中的路由名稱一致
  props: ["eventId", "sessionId"], // 接收路由傳來的 eventId 和 sessionId

  data() {
    return {
      // 確保 parsedSelectedSeats 始終被初始化為空陣列 []
      parsedSelectedSeats: [],
      parsedTotalAmount: 0,

      buyerName: "",

      isCreatingOrder: false,
      loading: true, // 初始設為 true，因為 created 鉤子會立即發送異步請求
      error: null,
    };
  },
  computed: {
    selectedSeatIds() {
      // 確保這裡仍然能獲取到 seat ID，用於傳遞給後端創建訂單
      return this.parsedSelectedSeats.map((seat) => seat.id);
    },
  },
  async created() {
    // 檢查是否有傳入必要的 ID
    if (!this.eventId || !this.sessionId) {
      this.error = "缺少訂單創建所需的信息，請返回活動頁面重新選擇。";
      this.loading = false; // 如果沒有必要資訊，就停止載入狀態
      return;
    }

    // 從後端獲取會話鎖定的座位資訊
    await this.fetchLockedSeats();
  },
  methods: {
    async fetchLockedSeats() {
      this.loading = true; // 在發送請求前設置為 true
      this.error = null;
      try {
        const response = await apiClient.get(
          `/api/events/${this.eventId}/seats/?session_id=${this.sessionId}&status=locked_by_session`
        );

        // 篩選出真正由當前會話鎖定的座位
        this.parsedSelectedSeats = response.data.filter(
          (seat) =>
            seat.status === "locked" &&
            seat.locked_by_session === this.sessionId
        );

        // 計算總金額
        this.parsedTotalAmount = this.parsedSelectedSeats.reduce(
          (sum, seat) => sum + parseFloat(seat.price),
          0
        );

        if (this.parsedSelectedSeats.length === 0) {
          this.error = "未找到已鎖定的座位，或鎖定已過期，請重新選擇。";
        }
      } catch (err) {
        this.error = "載入已鎖定座位信息失敗，請稍後再試。";
        if (
          axios.isAxiosError(err) &&
          err.response &&
          err.response.data &&
          err.response.data.message
        ) {
          this.error = err.response.data.message;
        }
        console.error("Error fetching locked seats:", err);
        // 如果載入失敗，清空座位數據，防止錯誤顯示
        this.parsedSelectedSeats = [];
        this.parsedTotalAmount = 0;
      } finally {
        this.loading = false; // 請求完成後設置為 false，無論成功或失敗
      }
    },

    async createOrder() {
      if (this.parsedSelectedSeats.length === 0) {
        this.error = "沒有選中的座位可以建立訂單。";
        return;
      }

      this.isCreatingOrder = true;
      this.loading = true; // 再次設置載入狀態
      this.error = null;

      try {
        const orderData = {
          seat_ids: this.selectedSeatIds,
          event_id: this.eventId,
          buyer_name: this.buyerName,
          session_id: this.sessionId, // 傳遞 session_id 給後端
        };

        const response = await apiClient.post("/api/orders/", orderData);

        if (response.status === 201) {
          alert("訂單建立成功！");
          this.$router.push({
            name: "OrderConfirmation",
            query: {
              orderId: response.data.id,
              orderNumber: response.data.order_number,
              totalAmount: response.data.total_amount,
              status: response.data.status,
            },
          });
          // 訂單成功後清除 localStorage 中的 session_id，結束本次會話
          localStorage.removeItem("session_id");
        }
      } catch (err) {
        this.error = "建立訂單失敗。";
        if (axios.isAxiosError(err) && err.response && err.response.data) {
          if (err.response.data.message) {
            this.error = err.response.data.message;
          }
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
        console.error("Error creating order:", err);
        // 如果訂單創建失敗，重新獲取座位狀態以反映最新情況
        await this.fetchLockedSeats();
      } finally {
        this.isCreatingOrder = false;
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.checkout-page {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  text-align: left;
}
.error-message {
  color: red;
  background-color: #ffe0e0;
  border: 1px solid red;
  padding: 10px;
  margin-bottom: 20px;
  border-radius: 5px;
}
.buyer-info-form {
  margin-top: 30px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}
.form-group {
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
.form-group input[type="text"] {
  width: calc(100% - 20px);
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
button[type="submit"] {
  background-color: #42b983;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  margin-top: 10px;
}
button[type="submit"]:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}
</style>
