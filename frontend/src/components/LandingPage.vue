<template>
  <div class="landing-page">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">{{ $t('landing.hero.title') }}</h1>
        <p class="hero-subtitle">{{ $t('landing.hero.subtitle') }}</p>
        <div class="hero-features">
          <div class="feature-item">
            <span class="feature-icon">⚡</span>
            <span>{{ $t('landing.hero.feature1') }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">🎯</span>
            <span>{{ $t('landing.hero.feature2') }}</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">💰</span>
            <span>{{ $t('landing.hero.feature3') }}</span>
          </div>
        </div>
        <button class="cta-button" @click="scrollToSection('how-it-works')">
          {{ $t('landing.hero.cta') }}
        </button>
      </div>
      <div class="hero-image phones">
        <div class="phone-mockup left">
          <div class="screen">
            <div class="telegram-header">Мой черновик</div>
            <div class="telegram-chat">
              <div class="message received raw">
                завтра хенкали сгрибами, закзы до12, доставка сч 17 до 21. безнал тожы можно. пиши в лс
              </div>
            </div>
          </div>
        </div>
        <!-- Arrow between phones -->
        <div class="phone-arrow" aria-label="taiger">
          <svg class="arrow-svg" viewBox="0 0 220 50" role="img" aria-label="taiger">
            <defs>
              <linearGradient id="arrowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#667eea" />
                <stop offset="100%" stop-color="#764ba2" />
              </linearGradient>
            </defs>
            <path d="M10 25 H185" stroke="url(#arrowGrad)" stroke-width="6" stroke-linecap="round" fill="none"/>
            <polygon points="185,15 210,25 185,35" fill="url(#arrowGrad)"/>
            <text x="95" y="33" text-anchor="middle" font-size="16" font-weight="700" fill="#5b5b5b">taiger</text>
          </svg>
        </div>
        <div class="phone-mockup right">
          <div class="screen">
            <div class="telegram-header">Домашние хинкали на заказ</div>
            <div class="telegram-chat">
              <div class="message sent improved">
                Уже завтра готовим свежие хинкали с грибами 🍄
                
                — Принимаем заказы до 12:00
                — Доставка сегодня с 17:00 до 21:00
                — Оплата наличными и по карте
                
                Напишите в личные сообщения — закрепим заказ и подскажем по порциям. Горячие, сочные и очень вкусные — как дома у бабушки 🤍
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section id="how-it-works" class="how-it-works">
      <div class="container">
        <h2>{{ $t('landing.howItWorks.title') }}</h2>
        <div class="steps">
          <div class="step" v-for="(step, index) in steps" :key="index">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-icon">{{ step.icon }}</div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Before/After Section -->
    <section class="before-after">
      <div class="container">
        <h2>{{ $t('landing.beforeAfter.title') }}</h2>
        <div class="comparison">
          <div class="before">
            <h3>{{ $t('landing.beforeAfter.before.title') }}</h3>
            <ul>
              <li v-for="item in beforeItems" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="arrow">→</div>
          <div class="after">
            <h3>{{ $t('landing.beforeAfter.after.title') }}</h3>
            <ul>
              <li v-for="item in afterItems" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Target Audience Section -->
    <section class="target-audience">
      <div class="container">
        <h2>{{ $t('landing.audience.title') }}</h2>
        <div class="audience-cards">
          <div class="audience-card" v-for="audience in audiences" :key="audience.key">
            <div class="audience-icon">{{ audience.icon }}</div>
            <h3>{{ audience.title }}</h3>
            <p>{{ audience.description }}</p>
            <div class="audience-benefits">
              <div class="benefit" v-for="benefit in audience.benefits" :key="benefit">
                ✓ {{ benefit }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section -->
    <section class="pricing credit" id="free-credit">
      <div class="container">
        <div class="credit-banner">
          <div class="credit-text">
            <h2>{{ $t('landing.credit.title') }}</h2>
            <p>{{ $t('landing.credit.subtitle') }}</p>
          </div>
          <button class="plan-button start" @click="startTrial">{{ $t('landing.credit.button') }}</button>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="faq">
      <div class="container">
        <h2>{{ $t('landing.faq.title') }}</h2>
        <div class="faq-items">
          <div class="faq-item" v-for="(faq, index) in faqs" :key="index">
            <div class="faq-question" @click="toggleFaq(index)">
              <span>{{ faq.question }}</span>
              <span class="faq-toggle" :class="{ 'open': faq.open }">+</span>
            </div>
            <div class="faq-answer" v-show="faq.open">
              <p>{{ faq.answer }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="final-cta">
      <div class="container">
        <h2>{{ $t('landing.finalCta.title') }}</h2>
        <p>{{ $t('landing.finalCta.subtitle') }}</p>
        <button class="cta-button large" @click="startTrial">
          {{ $t('landing.finalCta.button') }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const steps = computed(() => [
  {
    icon: '📱',
    title: t('landing.howItWorks.step1.title'),
    description: t('landing.howItWorks.step1.description')
  },
  {
    icon: '🧠',
    title: t('landing.howItWorks.step3.title'),
    description: t('landing.howItWorks.step3.description')
  },
  {
    icon: '✍️',
    title: t('landing.howItWorks.step4.title'),
    description: t('landing.howItWorks.step4.description')
  }
])

const beforeItems = computed(() => [
  t('landing.beforeAfter.before.item1'),
  t('landing.beforeAfter.before.item2'),
  t('landing.beforeAfter.before.item3'),
  t('landing.beforeAfter.before.item4')
])

const afterItems = computed(() => [
  t('landing.beforeAfter.after.item1'),
  t('landing.beforeAfter.after.item2'),
  t('landing.beforeAfter.after.item3'),
  t('landing.beforeAfter.after.item4')
])

const audiences = computed(() => [
  {
    key: 'bloggers',
    icon: '✍️',
    title: t('landing.audience.bloggers.title'),
    description: t('landing.audience.bloggers.description'),
    benefits: [
      t('landing.audience.bloggers.benefit1'),
      t('landing.audience.bloggers.benefit2'),
      t('landing.audience.bloggers.benefit3')
    ]
  },
  {
    key: 'entrepreneurs',
    icon: '💼',
    title: t('landing.audience.entrepreneurs.title'),
    description: t('landing.audience.entrepreneurs.description'),
    benefits: [
      t('landing.audience.entrepreneurs.benefit1'),
      t('landing.audience.entrepreneurs.benefit2'),
      t('landing.audience.entrepreneurs.benefit3')
    ]
  },
  {
    key: 'housewives',
    icon: '🏠',
    title: t('landing.audience.housewives.title'),
    description: t('landing.audience.housewives.description'),
    benefits: [
      t('landing.audience.housewives.benefit1'),
      t('landing.audience.housewives.benefit2'),
      t('landing.audience.housewives.benefit3')
    ]
  }
])



const faqs = ref([
  {
    question: t('landing.faq.q1.question'),
    answer: t('landing.faq.q1.answer'),
    open: false
  },
  {
    question: t('landing.faq.q2.question'),
    answer: t('landing.faq.q2.answer'),
    open: false
  },
  {
    question: t('landing.faq.q3.question'),
    answer: t('landing.faq.q3.answer'),
    open: false
  },
  {
    question: t('landing.faq.q4.question'),
    answer: t('landing.faq.q4.answer'),
    open: false
  },
  {
    question: t('landing.faq.q5.question'),
    answer: t('landing.faq.q5.answer'),
    open: false
  }
])

const scrollToSection = (sectionId: string) => {
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

const toggleFaq = (index: number) => {
  faqs.value[index].open = !faqs.value[index].open
}

const startTrial = () => {
  // Эмитируем событие для родительского компонента
  emit('start-trial')
}

const emit = defineEmits(['start-trial'])
</script>

<style scoped>
.landing-page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.landing-page::before {
  content: "";
  position: fixed;
  inset: 0;
  background: linear-gradient(120deg, #eef2ff 0%, #fdeaf5 40%, #e9fbf3 70%, #eef2ff 100%);
  background-size: 200% 200%;
  animation: landingGradient 28s ease infinite;
  z-index: -2;
  pointer-events: none;
}

.landing-page::after {
  content: "";
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.55) 0%, rgba(255, 255, 255, 0) 60%),
              radial-gradient(circle at 80% 30%, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0) 55%),
              radial-gradient(circle at 50% 80%, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0) 60%);
  z-index: -1;
  pointer-events: none;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* Hero Section */
.hero {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 80px 20px;
  display: flex;
  align-items: center;
  min-height: 80vh;
  max-width: 1400px;
  margin: 0 auto;
}

.hero-content {
  flex: 1;
  max-width: 600px;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.3rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

.hero-features {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
}

.feature-icon {
  font-size: 1.5rem;
}

.cta-button {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 15px 30px;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  box-shadow: 0 0 0 rgba(255, 107, 107, 0.45);
  animation: ctaGlow 8s ease-in-out infinite;
}

.cta-button:hover {
  background: #ff5252;
  transform: translateY(-2px);
}

.cta-button.large {
  padding: 20px 40px;
  font-size: 1.3rem;
}

.cta-button::before {
  content: "";
  position: absolute;
  inset: -30%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0) 60%);
  opacity: 0;
  transform: scale(0.6);
  transition: opacity 0.4s ease;
}

.cta-button:hover::before {
  opacity: 0.4;
}

@keyframes ctaGlow {
  0% {
    box-shadow: 0 0 0 rgba(255, 107, 107, 0.35);
    transform: translateZ(0);
  }
  50% {
    box-shadow: 0 0 35px rgba(255, 107, 107, 0.45);
  }
  100% {
    box-shadow: 0 0 0 rgba(255, 107, 107, 0.35);
  }
}

/* Phones layout */
.hero-image.phones {
  flex: 1;
  display: flex;
  gap: 24px;
  justify-content: center;
  align-items: center;
  max-width: 800px;
  margin: 0 auto;
}

.phone-mockup {
  width: 260px;
  height: 520px;
  background: #111;
  border-radius: 24px;
  padding: 16px;
  position: relative;
  box-shadow: 0 20px 60px rgba(0,0,0,0.35);
}

.phone-mockup.left { 
  transform: rotate(-3deg); 
}

.phone-mockup.right { 
  transform: rotate(3deg); 
}

.screen {
  width: 100%;
  height: 100%;
  background: #f6f7f9;
  border-radius: 18px;
  padding: 12px;
  overflow: hidden;
}

.telegram-header {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 14px;
  font-weight: 600;
  color: #222;
  font-size: 15px;
  background: #fff;
  border-radius: 8px 8px 0 0;
  margin-bottom: 8px;
}

.telegram-chat {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: calc(100% - 48px);
  overflow: hidden;
}

.message {
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 85%;
  font-size: 12px;
  line-height: 1.4;
}

.message.sent {
  background: #007bff;
  color: white;
  align-self: flex-end;
  margin-left: auto;
}

.message.received {
  background: white;
  color: #333;
  align-self: flex-start;
}

.message.raw { 
  background: #fff3cd; 
  color: #7a5d00; 
  border: 1px dashed #e0c46c; 
}

.message.improved { 
  background: #e7f8ee; 
  color: #1e7a3e; 
  border: 1px solid #bfe6cd; 
}

/* Arrow styles between phones */
.phone-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 70px;
  margin: 0 12px;
  flex-shrink: 0;
}

.arrow-svg { 
  width: 200px; 
  height: 70px; 
  filter: drop-shadow(0 3px 6px rgba(0,0,0,0.25));
}

/* How It Works Section */
.how-it-works {
  padding: 80px 0;
  background: rgba(248, 249, 250, 0.78);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

.how-it-works h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
}

.steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.step {
  text-align: center;
  padding: 2rem;
  background: white;
  border-radius: 15px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
  transition: transform 0.3s ease;
}

.step:hover {
  transform: translateY(-5px);
}

.step-number {
  display: inline-block;
  width: 40px;
  height: 40px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  line-height: 40px;
  font-weight: bold;
  margin-bottom: 1rem;
}

.step-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.step h3 {
  font-size: 1.3rem;
  margin-bottom: 1rem;
  color: #333;
}

.step p {
  color: #666;
  line-height: 1.6;
}

/* Before/After Section */
.before-after {
  padding: 80px 0;
  background: rgba(255, 255, 255, 0.82);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.before-after h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
}

.comparison {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 2rem;
  align-items: center;
}

.before, .after {
  padding: 2rem;
  border-radius: 15px;
}

.before {
  background: #ffebee;
}

.after {
  background: #e8f5e8;
}

.before h3, .after h3 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  text-align: center;
}

.before h3 {
  color: #d32f2f;
}

.after h3 {
  color: #388e3c;
}

.before ul, .after ul {
  list-style: none;
  padding: 0;
}

.before li, .after li {
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}

.before li:before {
  content: '❌ ';
  margin-right: 0.5rem;
}

.after li:before {
  content: '✅ ';
  margin-right: 0.5rem;
}

.arrow {
  font-size: 3rem;
  color: #667eea;
  font-weight: bold;
}

/* Target Audience Section */
.target-audience {
  padding: 80px 0;
  background: rgba(248, 249, 250, 0.78);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

.target-audience h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
}

.audience-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.audience-card {
  background: white;
  padding: 2rem;
  border-radius: 15px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
  text-align: center;
  transition: transform 0.3s ease;
}

.audience-card:hover {
  transform: translateY(-5px);
}

.audience-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.audience-card h3 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #333;
}

.audience-card p {
  color: #666;
  margin-bottom: 1.5rem;
}

.audience-benefits {
  text-align: left;
}

.benefit {
  padding: 0.5rem 0;
  color: #388e3c;
  font-weight: 500;
}

/* Pricing Section */
.pricing {
  padding: 80px 0;
  background: rgba(255, 255, 255, 0.82);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.pricing h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
}

.pricing-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.pricing-card {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 15px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
}

.pricing-card:hover {
  border-color: #667eea;
  transform: translateY(-5px);
}

.plan-header h3 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #333;
}

.price {
  font-size: 2.5rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 2rem;
}

.features {
  list-style: none;
  padding: 0;
  margin-bottom: 2rem;
}

.features li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.plan-button {
  width: 100%;
  padding: 15px;
  border: 2px solid #667eea;
  background: white;
  color: #667eea;
  border-radius: 50px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.plan-button:hover {
  background: #667eea;
  color: white;
}

.plan-button.popular {
  background: #667eea;
  color: white;
}

/* FAQ Section */
.faq {
  padding: 80px 0;
  background: rgba(248, 249, 250, 0.78);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

@keyframes landingGradient {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.faq h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  color: #333;
}

.faq-items {
  max-width: 800px;
  margin: 0 auto;
}

.faq-item {
  background: white;
  border-radius: 10px;
  margin-bottom: 1rem;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.faq-question {
  padding: 1.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  transition: background 0.3s ease;
}

.faq-question:hover {
  background: #f8f9fa;
}

.faq-toggle {
  font-size: 1.5rem;
  font-weight: bold;
  transition: transform 0.3s ease;
}

.faq-toggle.open {
  transform: rotate(45deg);
}

.faq-answer {
  padding: 0 1.5rem 1.5rem;
  color: #666;
  line-height: 1.6;
}

/* Final CTA Section */
.final-cta {
  padding: 80px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
}

.final-cta h2 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.final-cta p {
  font-size: 1.2rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

/* Responsive Design */
@media (max-width: 768px) {
  .hero {
    flex-direction: column;
    text-align: center;
    padding: 60px 20px;
  }
  
  .hero-title {
    font-size: 2.5rem;
  }
  
  .hero-image.phones { 
    gap: 16px; 
    margin-top: 2rem;
    max-width: 600px;
  }
  
  .phone-mockup {
    width: 200px;
    height: 400px;
  }
  
  .phone-arrow { 
    height: 50px; 
    margin: 0 8px;
  }
  
  .arrow-svg { 
    width: 140px; 
    height: 50px; 
  }
  
  .telegram-header {
    font-size: 13px;
    height: 36px;
    padding: 0 12px;
  }
  
  .telegram-chat {
    height: calc(100% - 44px);
    gap: 8px;
  }
  
  .message {
    font-size: 10px;
    padding: 8px 12px;
    line-height: 1.3;
  }
  
  .message.raw { 
    background: #fff3cd; 
    color: #7a5d00; 
    border: 1px dashed #e0c46c; 
  }
  
  .message.improved { 
    background: #e7f8ee; 
    color: #1e7a3e; 
    border: 1px solid #bfe6cd; 
  }
  
  .pricing.credit { background: #f8f9fa; }
  .credit-banner {
    display:flex; align-items:center; justify-content:space-between;
    background:white; border:2px solid #e0e0e0; border-radius:16px; padding:24px 28px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  }
  .credit-text h2 { font-size: 2rem; margin:0 0 8px; }
  .credit-text p { margin:0; color:#555; }
  .plan-button.start { width:auto; padding:14px 22px; }
  
  .hero-image.phones { gap: 12px; }
  .phone-mockup { width: 160px; height: 320px; }
  .credit-banner { flex-direction: column; gap: 16px; text-align:center; }
}
</style>