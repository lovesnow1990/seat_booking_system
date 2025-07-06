import { createRouter, createWebHistory } from "vue-router";
import EventList from "../views/EventList.vue";
import EventDetail from "../views/EventDetail.vue";
import Checkout from "../views/Checkout.vue";
import OrderConfirmation from "../views/OrderConfirmation.vue";

const routes = [
  {
    path: "/",
    name: "EventList",
    component: EventList,
  },
  {
    path: "/events/:id", // 使用 :id 作為動態路由參數
    name: "EventDetail",
    component: EventDetail,
    props: true, // 將路由參數作為 prop 傳遞給元件
  },
  {
    // *** 這裡是最關鍵的修改 ***
    // 定義 eventId 和 sessionId 作為路徑的一部分
    // ':eventId' 表示 eventId 是必填的路由參數
    // ':sessionId?' 表示 sessionId 是可選的路由參數（儘管我們總會傳送它）
    path: "/checkout",
    name: "SeatCheckout",
    component: Checkout,
    props: (route) => ({ ...route.query }),
  },
  {
    path: "/order-confirmation",
    name: "OrderConfirmation",
    component: OrderConfirmation,
    props: (route) => ({ ...route.query }),
  },
  {
    path: "/about",
    name: "About",
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: () =>
      import(/* webpackChunkName: "about" */ "../views/AboutView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

export default router;
