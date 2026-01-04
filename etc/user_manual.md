# 🐯 Taiger.pro User Manual

Welcome to Taiger.pro - your automated Telegram channel management assistant! This guide will help you understand how to use the service effectively to transform your draft posts into polished publications.

## 🎯 What is Taiger.pro?

Taiger.pro is a server application designed to help Telegram channel authors automate the transformation of draft posts into ready-to-publish content. The interface is designed for both beginners and advanced users - newcomers can get results in minutes, while experienced users can flexibly configure continuous processing.

## ✅ Prerequisites

Before you start using Taiger.pro, ensure you have:

- 💼 A Telegram account with administrator rights in the channels where the assistant will work
- 📱 Two channels: one for drafts (source) and one for publications (destination). You can create these in advance or through the rule wizard
- 🔐 Readiness to authenticate: via Telegram Mini App (TMA) or confirmation by phone and SMS/2FA

## 🚪 Getting Started

### 1. Accessing the Application
- Open the Taiger.pro web interface in your browser
- The language selection screen will load (🇺🇸/🇷🇺). Your preference is saved in the browser

### 2. Authentication Options
You have two ways to log in:

**Telegram Mini App (TMA) Authorization** 🤖
- If accessing from Telegram Mini App, the service will automatically request a token and log you in upon successful response

**Classic Login** 📞
- Enter your phone number and wait for the SMS code
- Enter the code, and provide the 2FA password if required
- New accounts will receive a welcome modal explaining how the assistant works

If you encounter a network error, a notification with a "Try Again" hint will appear - click the button to retry.

## 🧭 Interface Overview

After logging in, you'll see one of these UI modes:

### Original Interface 🖥️
The classic dashboard with blocks for balance, worker, logs, and rules.

### Redesigned Interface 🎨
Tabbed interface (Home, Activity, Channels, Settings). You can switch via Settings → "Enable New Interface".

#### Key Elements of the Redesign:
- **Home** 🏠 - Profile, balance, assistant status, and start/stop button
- **Activity** 📈 - Unified log stream: real-time, scheduled posts, errors
- **Channels** 🔁 - Rule management through ChannelPairs component and floating "➕" button to launch the wizard
- **Settings** ⚙️ - Logout, design switching, TMA data update, help link
- **Notifications** 🔔 - Appear in the top right corner, automatically hide, and duplicate successes/errors

## 🚀 Quick Start (For Beginners)

1. **Check Channel Access** - Ensure the assistant has administrator rights in both draft and publication channels
2. **Open Channels → ➕** - Launch the rule creation wizard
3. **Complete the 2-Step Wizard**:
   - Step 1: Select source channel (drafts)
   - Step 2: Create target channel (publication) and configure
4. **Monitor Progress** 🕘 - An indicator will show: worker stopping → saving → starting
5. **Confirmation** 💬 - Notification "Rule created and assistant started!" and active "running" status

## 🤖 Assistant Management

- The start/stop button is available in the "Assistant Status" block (Dashboard/Home)
- Status indicators:
  - `running` (🟢 active)
  - `stopped` (🔴 stopped)
  - `starting/stopping` (🟡 switching)
  - `auth_required` (🔒 re-authentication needed)
  - `error` (⚠️ error occurred)
- The button is disabled if there are no active rules or balance < 0
- To change accounts in TMA, use Settings → "Refresh Account"

## 📊 Monitoring and Logs

- **Activity** tab or "Logs" block shows events in chronological order
- Color indicators:
  - Green - success
  - Red - error
  - Yellow - warning
  - Blue - information
- Hover over entries or open notifications for details
- Scheduled posts and worker errors (e.g., insufficient funds) appear in separate sections

## ✏️ Working with Rules

- **ChannelPairs** displays all current channel pairs
- Use contextual buttons within cards for editing, deletion, and cloning
- Real-time validation alerts you if a channel is unavailable or you lack permissions
- Progress indicators and notifications inform you of each step during rule creation/editing

## 🔄 Switching Interface Modes

- In Settings, enable or disable "Redesigned UI"
- The switch happens immediately without reloading
- Settings are saved in `localStorage`, so your last mode will be selected on next login

## 🛠️ Common Issues and Solutions

- **No SMS Code**: Ensure the number includes the country code and request again after 60 seconds
- **"auth_required" Message**: Log out via Settings → Logout and log back in
- **"insufficient_funds" Status in Logs**: Top up your Telegram balance and restart the assistant
- **Logs Not Updating**: Check WebSocket connection; fallback polling activates if unavailable
- **Changed Account in Telegram Mini App**: Click "Refresh Account" to request a new token

## 📱 Mobile Access

- All main elements adapt to smartphone screens
- Notifications expand to screen width, and the floating "➕" button is fixed at the bottom right
- Login and rule wizard support touch gestures and virtual keyboard

## 💡 Productivity Tips

- Use **Simple Mode** for batch processing: prepare posts in drafts and process them when convenient
- In **Advanced Mode**, configure detailed schedules and multiple channels for regular automation
- Regularly check the Activity tab to track how AI improves content and respond quickly to errors

## 🧭 Navigation Guide

### Home Tab 🏠
- View your profile information including VIP level and balance
- Control your assistant's status (start/stop)
- See warnings if no rules are configured
- View the last log entry from your assistant

### Activity Tab 📈
- View all system logs in chronological order
- Filter by log type (all, info, warnings, errors)
- Expand log entries to see detailed information
- Copy error details for troubleshooting

### Channels Tab 🔁
- Manage your channel pairs (rules)
- Create new rules with the wizard (➕ button)
- Edit or delete existing rules
- View rule details and status

### Settings Tab ⚙️
- Toggle between classic and redesigned interface
- Refresh your Telegram account information
- Access help documentation
- Log out of the application

## 🔄 Rule Creation Wizard

The rule creation wizard guides you through setting up automated post processing:

### Step 1: Draft Channel
- Create a new draft channel or select an existing one
- Draft channels store your raw content before processing

### Step 2: Target Channel
- Create a new publication channel or select an existing one
- Configure posting schedule (minimum and maximum delays)
- Set up AI processing parameters

## 🤖 Assistant States Explained

- **Running (🟢)**: The assistant is actively monitoring your channels and processing posts
- **Stopped (🔴)**: The assistant is inactive and not processing any content
- **Starting/Stopping (🟡)**: The assistant is transitioning between states
- **Auth Required (🔒)**: Your Telegram session has expired and requires re-authentication
- **Error (⚠️)**: An error has occurred that requires attention

## 💰 Balance and VIP System

- Your balance determines how many posts can be processed
- VIP levels provide benefits like higher processing priority
- Monitor your balance in the Home tab
- Insufficient funds will pause processing with clear error notifications

Success in automating your Telegram channels! 🚀