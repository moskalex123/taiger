// Environment variable utilities for UI switching
export const getEnvVar = (name: string, defaultValue: string = ''): string => {
  // In Vite, environment variables are available via import.meta.env
  return (import.meta.env as any)[name] || defaultValue
}

export const isRedesignEnabled = (): boolean => {
  // Check environment variable first
  const envSetting = getEnvVar('VITE_ENABLE_REDESIGN', 'false')
  console.log('🔧 Environment check:', {
    'VITE_ENABLE_REDESIGN': envSetting,
    'All env vars': import.meta.env
  })
  
  if (envSetting.toLowerCase() === 'true') {
    console.log('✅ Redesign enabled via environment variable')
    return true
  }
  
  // Check localStorage for user preference (overrides env)
  const userPreference = localStorage.getItem('enable_redesigned_ui')
  console.log('🔧 localStorage check:', userPreference)
  
  if (userPreference !== null) {
    const enabled = userPreference === 'true'
    console.log(`✅ Using localStorage preference: ${enabled}`)
    return enabled
  }
  
  console.log('❌ Redesign disabled - no environment variable or localStorage setting found')
  // Default to false if no setting found
  return false
}

export const setRedesignPreference = (enabled: boolean): void => {
  localStorage.setItem('enable_redesigned_ui', enabled.toString())
}

export const clearRedesignPreference = (): void => {
  localStorage.removeItem('enable_redesigned_ui')
}

// Query param helper
export const getQueryParam = (name: string): string | null => {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get(name)
}

// Enable backdoor autologin for web mode (non-TMA) when true
export const isBackdoorAutologinEnabled = (): boolean => {
  const envSetting = getEnvVar('VITE_ENABLE_BACKDOOR_AUTOLOGIN', 'false').toLowerCase() === 'true'
  const lsSetting = localStorage.getItem('enable_backdoor_autologin') === 'true'
  const qpSetting = (getQueryParam('backdoor') || '').toLowerCase() === '1'
  return envSetting || lsSetting || qpSetting
}

export const setBackdoorAutologinPreference = (enabled: boolean): void => {
  localStorage.setItem('enable_backdoor_autologin', enabled ? 'true' : 'false')
}

export const clearBackdoorAutologinPreference = (): void => {
  localStorage.removeItem('enable_backdoor_autologin')
}