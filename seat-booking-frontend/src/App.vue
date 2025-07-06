<template>
  <div id="app">
    <nav>
      <router-link to="/">活動列表</router-link> |
      <router-link to="/about">關於</router-link>
      <!-- 您可以在這裡添加更多導航鏈接，例如到訂單查詢頁面 -->
    </nav>
    <router-view />
  </div>
</template>

<script>
export default {
  name: "App",
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
nav {
  padding: 30px;
}
nav a {
  font-weight: bold;
  color: #2c3e50;
}
nav a.router-link-exact-active {
  color: #42b983;
}
</style>
