<template>
  <div class="worker-queue">
    <!-- Active Workers -->
    <div class="active-workers">
      <div class="section-title">{{ $t('active_workers') }}:</div>
      <div class="worker-list">
        <span 
          v-for="workerId in activeWorkers" 
          :key="workerId"
          :class="['worker-id', { 
            'current-user': workerId === currentUserId, 
            'starting': getWorkerStatus(workerId) === 'starting',
            'newcomer': isWorkerNewcomer(workerId)
          }]"
          :style="getWorkerStyle(workerId)">
          <span v-if="isWorkerNewcomer(workerId)" class="newcomer-badge">🌟</span>
          {{ workerId }}<span v-if="getWorkerStatus(workerId) === 'starting'" class="status-indicator"> ({{ $t('starting') }})</span>
        </span>
        <span v-if="activeWorkers.length === 0" class="no-workers">{{ $t('no_active_workers') }}</span>
      </div>
    </div>



    <!-- Queue -->
    <div class="queue-section">
      <div class="section-title">{{ $t('queue') }}:</div>
      <div class="worker-list">
        <span 
          v-for="workerId in queueWorkers" 
          :key="workerId"
          :class="['worker-id', { 
            'current-user': workerId === currentUserId,
            'newcomer': isWorkerNewcomer(workerId)
          }]"
          :style="getWorkerStyle(workerId)"
          :title="isWorkerNewcomer(workerId) ? $t('newcomer_priority') : `VIP ${getWorkerVip(workerId)}`">
          <span v-if="isWorkerNewcomer(workerId)" class="newcomer-badge">🌟</span>
          {{ workerId }}
        </span>
        <span v-if="queueWorkers.length === 0" class="no-workers">{{ $t('queue_empty') }}</span>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { useVipStyles } from '../composables/useVipStyles';
import { useI18n } from 'vue-i18n';

// Initialize i18n
const { t: $t } = useI18n();

interface QueueInfo {
  active_workers: number[];
  queue: number[];
  worker_vips: { [key: number]: number };
  worker_statuses: { [key: number]: string };
  worker_newcomers: { [key: number]: boolean };
  worker_priorities: { [key: number]: { priority: number; reason: string; is_newcomer: boolean } };
}

const props = defineProps<{
  currentUserId?: number;
}>();

const activeWorkers = ref<number[]>([]);
const queueWorkers = ref<number[]>([]);
const workerVips = ref<{ [key: number]: number }>({});
const workerStatuses = ref<{ [key: number]: string }>({});
const workerNewcomers = ref<{ [key: number]: boolean }>({});
const workerPriorities = ref<{ [key: number]: { priority: number; reason: string; is_newcomer: boolean } }>({});
const previousWorkerStatuses = ref<{ [key: number]: string }>({});
const error = ref<string | null>(null);
const refreshInterval = ref<number | null>(null);

// Use VIP styles composable
const vipStyles = useVipStyles();

const getWorkerVip = (workerId: number): number => {
  return workerVips.value[workerId] || 0;
};

const getWorkerStatus = (workerId: number): string => {
  return workerStatuses.value[workerId] || 'unknown';
};

const isWorkerNewcomer = (workerId: number): boolean => {
  return workerNewcomers.value[workerId] || false;
};

const getWorkerPriority = (workerId: number) => {
  return workerPriorities.value[workerId] || { priority: 0, reason: 'regular', is_newcomer: false };
};

const getWorkerStyle = (workerId: number) => {
  const isNewcomer = isWorkerNewcomer(workerId);
  if (isNewcomer) {
    return {
      backgroundColor: '#FFD700',
      color: '#000',
      fontWeight: 'bold',
      border: '2px solid #FFA500',
      boxShadow: '0 0 8px rgba(255, 215, 0, 0.6)'
    };
  }
  return vipStyles.getVipStyle(getWorkerVip(workerId));
};

const playSound = async (soundName: string) => {
  try {
    const audio = new Audio(`/sounds/${soundName}.mp3`);
    audio.volume = 0.5;
    
    // Preload the audio
    audio.load();
    
    // Wait for audio to be ready and play
    await new Promise((resolve, reject) => {
      audio.addEventListener('canplaythrough', resolve, { once: true });
      audio.addEventListener('error', reject, { once: true });
    });
    
    const playPromise = audio.play();
    if (playPromise !== undefined) {
      await playPromise;
      console.log(`Sound ${soundName} played successfully`);
    }
  } catch (e) {
    console.log(`Sound playback error for ${soundName}:`, e);
    // Fallback: try to play without waiting
    try {
      const fallbackAudio = new Audio(`/sounds/${soundName}.mp3`);
      fallbackAudio.volume = 0.3;
      fallbackAudio.play();
    } catch (fallbackError) {
      console.log('Fallback sound also failed:', fallbackError);
    }
  }
};

const fetchQueueInfo = async () => {
  try {
    const response = await axios.get<QueueInfo>('/api/queue/info', { withCredentials: true });
    const data = response.data;
    
    // Check if current user just moved to running status (from queue)
    if (props.currentUserId !== undefined) {
      const previousStatus = workerStatuses.value[props.currentUserId];
      const currentStatus = data.worker_statuses[props.currentUserId];
      
      if ((currentStatus === 'running' || currentStatus === 'active') && 
          previousStatus !== 'running' && previousStatus !== 'active') {
        // User moved to running/active status - play work sound
        await playSound('work');
      }
    }
    
    // Обновляем данные
    workerVips.value = data.worker_vips || {};
    workerStatuses.value = data.worker_statuses || {};
    workerNewcomers.value = data.worker_newcomers || {};
    workerPriorities.value = data.worker_priorities || {};
    
    // Разделяем воркеров: активные (running) + starting воркеры показываем как активных
    const baseActiveWorkers = data.active_workers || [];
    const startingWorkers = (data.queue || []).filter(workerId => 
      workerStatuses.value[workerId] === 'starting'
    );
    activeWorkers.value = [...baseActiveWorkers, ...startingWorkers];
    
    // В очереди показываем только pending воркеров
    queueWorkers.value = (data.queue || []).filter(workerId => 
      workerStatuses.value[workerId] !== 'starting'
    );
    
    previousWorkerStatuses.value = { ...workerStatuses.value };
    
    error.value = null;
  } catch (err: any) {
    console.error('Failed to fetch queue info:', err);
    error.value = $t('failed_load_queue');
  }
};

const startRefreshInterval = () => {
  refreshInterval.value = window.setInterval(fetchQueueInfo, 5000); // Update every 5 seconds
};

const stopRefreshInterval = () => {
  if (refreshInterval.value) {
    window.clearInterval(refreshInterval.value);
    refreshInterval.value = null;
  }
};

onMounted(() => {
  fetchQueueInfo();
  startRefreshInterval();
});

onUnmounted(() => {
  stopRefreshInterval();
});
</script>

<style scoped>
.worker-queue {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.active-workers, .queue-section {
  margin-bottom: 15px;
}

.section-title {
  font-weight: bold;
  margin-bottom: 8px;
  font-size: 16px;
}

.worker-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.worker-id {
  padding: 4px 8px;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid #ccc;
  font-weight: bold;
  font-size: 14px;
}

.worker-id.current-user {
  text-decoration: underline;
  text-decoration-thickness: 2px;
}

.worker-id.starting {
  background-color: rgba(255, 193, 7, 0.3);
  border-color: #ffc107;
}

.status-indicator {
  font-size: 12px;
  color: #856404;
  font-weight: normal;
}

.worker-id.newcomer {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #000;
  font-weight: bold;
  border: 2px solid #FF8C00;
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.7);
  animation: newcomer-glow 2s ease-in-out infinite alternate;
}

.newcomer-badge {
  margin-right: 4px;
  font-size: 16px;
  animation: star-twinkle 1.5s ease-in-out infinite alternate;
}

@keyframes newcomer-glow {
  from {
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.7);
  }
  to {
    box-shadow: 0 0 15px rgba(255, 215, 0, 1);
  }
}

@keyframes star-twinkle {
  from {
    opacity: 0.8;
    transform: scale(1);
  }
  to {
    opacity: 1;
    transform: scale(1.1);
  }
}



.no-workers {
  color: #666;
  font-style: italic;
}

.error-message {
  color: #d32f2f;
  background-color: #ffebee;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #f8bbd9;
  margin-top: 10px;
}
</style>