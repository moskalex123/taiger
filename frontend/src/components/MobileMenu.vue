<template>
  <div class="mobile-menu" v-if="isMobile">
    <div class="mobile-menu-header">
      <h3>{{ $t('dashboard') }}</h3>
      <button @click="toggleMenu" class="menu-toggle">
        <svg v-if="!isMenuOpen" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
        <svg v-else class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
    
    <div class="mobile-menu-content" :class="{ 'menu-open': isMenuOpen }">
      <div class="menu-section">
        <h4>{{ $t('language') }}</h4>
        <select v-model="currentLanguage" @change="changeLanguage" class="language-select">
          <option value="ru">🇷🇺 Русский</option>
          <option value="en">🇺🇸 English</option>
        </select>
      </div>
      
      <div class="menu-section">
        <button @click="scrollToSection('worker-controls')" class="menu-item">
          {{ $t('status_of_worker') }}
        </button>
        <button @click="scrollToSection('logs')" class="menu-item">
          {{ $t('logs') }}
        </button>
        <button @click="scrollToSection('channel-rules')" class="menu-item">
          {{ $t('channel_pair_rules') }}
        </button>
      </div>
      
      <div class="menu-section">
        <button @click="logout" class="menu-item logout-item">
          {{ $t('logout_and_reauth') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';

const { t: $t, locale } = useI18n();

const isMenuOpen = ref(false);
const isMobile = ref(false);
const currentLanguage = ref(locale.value);

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768;
  if (!isMobile.value) {
    isMenuOpen.value = false;
  }
};

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
};

const changeLanguage = () => {
  locale.value = currentLanguage.value;
  localStorage.setItem('preferred_language', currentLanguage.value);
  Cookies.set('language', currentLanguage.value, { expires: 365 });
};

const scrollToSection = (sectionId: string) => {
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' });
  }
  isMenuOpen.value = false;
};

const logout = async () => {
  try {
    localStorage.removeItem('token');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/';
  } catch (error) {
    console.error('Error during logout:', error);
    window.location.href = '/';
  }
};

onMounted(() => {
  checkMobile();
  window.addEventListener('resize', checkMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile);
});
</script>

<style scoped>
.mobile-menu {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #e0e0e0;
  margin-bottom: 10px;
}

.mobile-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
}

.mobile-menu-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.menu-toggle {
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.menu-toggle:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.icon {
  width: 24px;
  height: 24px;
  stroke-width: 2;
}

.mobile-menu-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  background: white;
}

.mobile-menu-content.menu-open {
  max-height: 400px;
  border-top: 1px solid #e0e0e0;
}

.menu-section {
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.menu-section:last-child {
  border-bottom: none;
}

.menu-section h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.language-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  background: white;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 12px 0;
  background: none;
  border: none;
  text-align: left;
  font-size: 16px;
  color: #333;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s;
  margin-bottom: 5px;
}

.menu-item:hover {
  background-color: rgba(0, 123, 255, 0.1);
  color: #007bff;
}

.logout-item {
  color: #dc3545;
  font-weight: 600;
}

.logout-item:hover {
  background-color: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}

@media (min-width: 769px) {
  .mobile-menu {
    display: none;
  }
}
</style>