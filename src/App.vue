<template>
  <div id="app">
    <MappingTool />
    <footer>
      <p>Author: szc</p>
    </footer>
  </div>
</template>

<script>
import MappingTool from './components/MappingTool.vue';

export default {
  name: 'App',
  components: {
    MappingTool,
  },
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
</style>
