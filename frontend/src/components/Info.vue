<template>
  <div class="info-page">
    <h2>{{ $t('info') }}</h2>
    
    <!-- Contact for funds -->
    <div class="contact-info">
      <div class="contact-message">
        {{ $t('contact_for_funds') }}: <a href="https://t.me/magellanvs" target="_blank" class="contact-link">@magellanvs</a>
      </div>
    </div>
    
    <!-- VIP Levels Table -->
    <div class="vip-section">
      <h3>{{ $t('vip_levels') }}</h3>
      <div class="vip-table">
        <table>
          <thead>
            <tr>
              <th>{{ $t('vip_level') }}</th>
              <th>{{ $t('vip_condition') }}</th>
              <th>{{ $t('agent_timeout') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr class="vip-row">
              <td class="vip-level">0</td>
              <td class="vip-condition">{{ $t('vip_0_condition') }}</td>
              <td class="vip-timeout">{{ vipTimeouts.vip0 }} {{ $t('minutes') }}</td>
            </tr>
            <tr class="vip-row">
              <td class="vip-level">1</td>
              <td class="vip-condition">{{ $t('vip_1_condition') }}</td>
              <td class="vip-timeout">{{ vipTimeouts.vip1 }} {{ $t('minutes') }}</td>
            </tr>
            <tr class="vip-row">
              <td class="vip-level">2</td>
              <td class="vip-condition">{{ $t('vip_2_condition') }}</td>
              <td class="vip-timeout">{{ vipTimeouts.vip2 }} {{ $t('minutes') }}</td>
            </tr>
            <tr class="vip-row">
              <td class="vip-level">3</td>
              <td class="vip-condition">{{ $t('vip_3_condition') }}</td>
              <td class="vip-timeout">{{ vipTimeouts.vip3 }} {{ $t('minutes') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pricing Table -->
    <div class="pricing-section">
      <h3>{{ $t('pricing_table') }}</h3>
      <div v-if="loading" class="loading">{{ $t('loading') }}</div>
      <div v-else-if="error" class="error-message">
        <p>{{ $t('error') }}: {{ error }}</p>
      </div>
      <div v-else-if="models.length > 0" class="pricing-table">
        <table>
          <thead>
            <tr>
              <th>{{ $t('model') }}</th>
              <th>{{ $t('price_per_post') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in models" :key="model.id" class="model-row">
              <td class="model-name">{{ model.model }}</td>
              <td class="model-price">
                <PriceDisplay 
                  :price="model.price_per_post || 0" 
                  :decimals="3"
                  price-class="model-price"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="no-data">
        <p>{{ $t('no_pricing_data') }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import axios from 'axios';
import { useI18n } from 'vue-i18n';
import PriceDisplay from './PriceDisplay.vue';

interface Model {
  id: number;
  model: string;
  price_per_post: number | null;
}

export default defineComponent({
  name: 'Info',
  components: {
    PriceDisplay
  },
  setup() {
    // Initialize i18n
    const { t: $t } = useI18n();

    const models = ref<Model[]>([]);
    const loading = ref(true);
    const error = ref<string | null>(null);

    // VIP timeout values from .env
    const vipTimeouts = ref({
      vip0: 5,  // VIP_0_TIMEOUT=5
      vip1: 10, // VIP_1_TIMEOUT=10
      vip2: 20, // VIP_2_TIMEOUT=20
      vip3: 30  // VIP_3_TIMEOUT=30
    });

    const fetchModels = async () => {
      try {
        loading.value = true;
        error.value = null;
        // Support both cookie-based auth and token-based auth (for TMA)
        const token = localStorage.getItem('auth_token');
        const headers: any = {};
        
        if (token) {
          headers['Authorization'] = 'Bearer ' + token;
        }
        
        const response = await axios.get('/api/channel_pairs/models', {
          withCredentials: true,
          headers
        });
        models.value = response.data;
      } catch (err: any) {
        console.error('Error fetching models:', err);
        error.value = err.response?.data?.detail || 'Failed to fetch pricing data';
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchModels();
    });

    return {
      models,
      loading,
      error,
      vipTimeouts,
      fetchModels,
      $t
    };
  }
});
</script>

<style scoped>
.info-page {
  padding: 20px;
  font-family: sans-serif;
  background: linear-gradient(to bottom, hwb(194 80% 8%), hsl(127, 63%, 80%));
  margin: 10px;
  width: calc(100% - 20px);
  min-height: calc(100vh - 220px);
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  box-sizing: border-box;
}

h2 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
  text-shadow: 1px 1px 0px rgba(225, 217, 217, 0.8), 1px 1px 1px rgba(84, 94, 101, 0.6);
}

.contact-info {
  background: rgba(255, 255, 255, 0.9);
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 25px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 2px solid rgba(76, 175, 80, 0.3);
}

.contact-message {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.contact-link {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
  transition: color 0.2s ease;
}

.contact-link:hover {
  color: #0056b3;
  text-decoration: underline;
}

.pricing-section {
  margin-top: 30px;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h3 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
  font-size: 1.5em;
}

.loading, .error-message {
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 15px;
  text-align: center;
}

.loading {
  background-color: #e0e0e0;
  color: #666;
}

.error-message {
  background-color: #ffdddd;
  color: #d8000c;
  border: 1px solid #d8000c;
}

.pricing-table {
  overflow-x: auto;
}

.pricing-table table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 auto;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.pricing-table th,
.pricing-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.pricing-table th {
  background-color: #f8f9fa;
  font-weight: bold;
  color: #333;
  border-bottom: 2px solid #007bff;
}

.model-row:hover {
  background-color: #f5f5f5;
}

.model-name {
  font-weight: 500;
  color: #333;
}

.model-price {
  font-weight: bold;
  color: #007bff;
  text-align: right;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #666;
  font-style: italic;
}

.no-data p {
  margin: 0;
  font-size: 16px;
}

.vip-section {
  margin-top: 30px;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.vip-table {
  overflow-x: auto;
}

.vip-table table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 auto;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.vip-table th,
.vip-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.vip-table th {
  background-color: #f8f9fa;
  font-weight: bold;
  color: #333;
  border-bottom: 2px solid #28a745;
}

.vip-row:hover {
  background-color: #f5f5f5;
}

.vip-level {
  font-weight: bold;
  color: #28a745;
  text-align: center;
  font-size: 18px;
}

.vip-condition {
  color: #333;
}

.vip-timeout {
  font-weight: bold;
  color: #007bff;
  text-align: center;
}

/* Mobile styles */
@media (max-width: 768px) {
  .contact-info {
    padding: 12px;
    margin-bottom: 20px;
  }
  
  .contact-message {
    font-size: 14px;
  }
  
  .info-page {
    padding: 15px;
    margin: 5px;
    width: calc(100% - 10px);
  }
}
</style>