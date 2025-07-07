<template>
  <div class="event-list">
    <h1>近期活動</h1>
    <p v-if="loading">載入中...</p>
    <p v-if="error">{{ error }}</p>
    <div v-if="events.length">
      <div v-for="event in events" :key="event.id" class="event-card">
        <h2>{{ event.name }}</h2>
        <p>地點：{{ event.venue_name }}</p>
        <p>時間：{{ getFormattedEventTime(event) }}</p>
        <router-link :to="{ name: 'EventDetail', params: { id: event.id } }">
          查看座位與預訂
        </router-link>
      </div>
    </div>
    <p v-else-if="!loading && !error">目前沒有可用的活動。</p>
  </div>
</template>

<script>
import apiClient from "@/api";

export default {
  name: "EventList",
  data() {
    return {
      events: [],
      loading: true,
      error: null,
    };
  },
  methods: {
    getFormattedEventTime(event) {
      if (event && event.event_date && event.event_time) {
        const dateTimeStr = `${event.event_date}T${event.event_time}`;
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
  },
  async created() {
    try {
      const response = await apiClient.get(`/api/events/`);
      this.events = response.data;
    } catch (err) {
      this.error = "載入活動失敗，請稍後再試。";
      console.error("Error fetching events:", err);
    } finally {
      this.loading = false;
    }
  },
};
</script>

<style scoped>
.event-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.event-card {
  border: 1px solid #eee;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: left;
}
.event-card h2 {
  color: #3498db;
  margin-top: 0;
}
</style>
