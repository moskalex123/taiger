// Simulate checking UI state as it would be done in the browser
const fs = require('fs');
const path = require('path');

// Read .env file
const envPath = path.join(__dirname, 'frontend', '.env');
const envContent = fs.readFileSync(envPath, 'utf8');

// Parse environment variables
const envLines = envContent.split('\n');
let envVars = {};
envLines.forEach(line => {
    if (line.includes('=') && !line.startsWith('#')) {
        const [key, value] = line.split('=');
        envVars[key.trim()] = value.trim();
    }
});

console.log('Environment variables from .env:');
console.log(envVars);

// Simulate localStorage (in a real browser, this would be window.localStorage)
// For this simulation, we'll assume localStorage is empty
const localStorage = {
    'enable_redesigned_ui': null // Change this to 'true' or 'false' to simulate localStorage values
};

console.log('\nSimulated localStorage:');
console.log(localStorage);

// Simulate isRedesignEnabled() function
function isRedesignEnabled() {
    // Check environment variable first
    const envSetting = envVars.VITE_ENABLE_REDESIGN || 'false';
    console.log('\nEnvironment check:');
    console.log('VITE_ENABLE_REDESIGN:', envSetting);
    
    if (envSetting.toLowerCase() === 'true') {
        console.log('✅ Redesign enabled via environment variable');
        return true;
    }
    
    // Check localStorage for user preference (overrides env)
    const userPreference = localStorage['enable_redesigned_ui'];
    console.log('localStorage check:', userPreference);
    
    if (userPreference !== null) {
        const enabled = userPreference === 'true';
        console.log(`✅ Using localStorage preference: ${enabled}`);
        return enabled;
    }
    
    console.log('❌ Redesign disabled - no environment variable or localStorage setting found');
    return false;
}

console.log('\n=== UI State Check ===');
const isEnabled = isRedesignEnabled();
console.log('\n=== Result ===');
console.log(`UI Redesign is ${isEnabled ? 'ENABLED' : 'DISABLED'}`);

if (isEnabled) {
    console.log('\n✅ The new redesigned UI should be active');
} else {
    console.log('\n🔴 The original UI should be active');
}