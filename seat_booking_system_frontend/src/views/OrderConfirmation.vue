<template>
  <div class="order-confirmation-page">
    <h1>訂單已送出！</h1>
    <p>您的訂單已成功建立，感謝您的預訂！</p>
    <div class="order-details">
      <p><strong>訂單編號:</strong> {{ orderNumber }}</p>
      <p><strong>訂單狀態:</strong> {{ status }}</p>
      <p><strong>總金額:</strong> {{ totalAmount }} NTD</p>
      <p>您可以在後台或通過訂單查詢功能查看訂單詳情。</p>
    </div>
    <router-link to="/">返回活動列表</router-link>
  </div>
</template>

<script>
export default {
  name: "OrderConfirmation",
  props: ["orderId", "orderNumber", "totalAmount", "status"], // 從路由接收訂單信息
  mounted() {
    // 您可以在這裡做一些清理工作，例如清空本地儲存的選座信息
  },
};
</script>

<style scoped>
.order-confirmation-page {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  text-align: center;
}
.order-details {
  border: 1px solid #eee;
  padding: 20px;
  margin-top: 20px;
  border-radius: 8px;
  background-color: #f9f9f9;
  text-align: left;
}
.order-details p {
  margin-bottom: 10px;
}
</style>
