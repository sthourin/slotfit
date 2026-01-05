# SlotFit Android App

Native Android app for SlotFit workout planning and tracking.

## Features

- Offline-first architecture with Room database
- Bluetooth Low Energy (BLE) heart rate monitoring (Polar H10)
- Slot-based workout routines
- AI-powered exercise recommendations
- Real-time heart rate display with zone tracking
- Workout state management (pause/resume, auto-save, crash recovery)
- Slot navigation (skip, re-order, return to skipped slots)
- Superset support (visual grouping, shared rest timer)

## Setup

1. **Prerequisites:**
   - Android Studio Hedgehog (2023.1.1) or later
   - JDK 17 or later
   - Android SDK 26+ (minimum), 34 (target)

2. **Open project:**
   - Open Android Studio
   - Select "Open an Existing Project"
   - Navigate to `android/` directory

3. **Sync Gradle:**
   - Android Studio will automatically sync Gradle
   - Wait for dependencies to download

4. **Run:**
   - Connect Android device (API 26+) or start emulator
   - Click Run button or press Shift+F10

## Project Structure

```
android/app/src/main/java/com/slotfit/app/
├── data/          # Room database, repositories, DAOs
├── ui/            # UI components, activities, fragments
├── bluetooth/      # BLE heart rate monitoring
├── sync/          # Offline sync (future phase)
└── services/      # Background services
```

## Development

- **Language**: Kotlin
- **Min SDK**: 26 (Android 8.0)
- **Target SDK**: 34 (Android 14)
- **Database**: Room (SQLite)
- **Architecture**: MVVM with LiveData/Flow
- **BLE**: Android BLE APIs for Polar H10
- **State Management**: ViewModel + LiveData/StateFlow

## Permissions

- `BLUETOOTH` - Required for BLE scanning
- `BLUETOOTH_SCAN` - Required for BLE scanning (Android 12+)
- `BLUETOOTH_CONNECT` - Required for BLE connection (Android 12+)
- `ACCESS_FINE_LOCATION` - Required for BLE on Android 6.0+

## Notes

- MVP is offline-only (no authentication/sync initially)
- Heart rate data captured at 1Hz (1 reading per second)
- Raw HR time-series data dropped after analytics generated
