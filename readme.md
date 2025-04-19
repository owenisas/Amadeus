# Setting Up Salieri AI

---

## Prerequisites

Ensure you have installed or have access to the following components on your system:

- **Node.js**  
  Install the latest stable version from the [Node.js website](https://nodejs.org/). Verify by running:
  ```bash
  node -v
  npm -v
  ```

- **Python 3**  
  Python is required for your automation scripts (and any Python‑based testing frameworks you might employ).  
  - To verify your Python installation:
    ```bash
    python3 --version
    ```
  - If Python is not installed, download it from [python.org](https://www.python.org/) or install via your package manager (e.g., `brew install python` on macOS).

- **Android Studio**  
  Download and install Android Studio from [developer.android.com/studio](https://developer.android.com/studio). Android Studio installs the Android SDK, which is necessary for running the emulator and for Appium’s interaction with Android devices.

- **Appium**  
  Appium is installed via npm and is the core tool for mobile test automation.

---

## Step 0: Configure Environment Variables (ANDROID_HOME)

Setting the `ANDROID_HOME` variable ensures that Android Studio, Appium, and related tools can locate your Android SDK. Follow the instructions for your operating system:

### On macOS or Linux

1. **Open your shell configuration file:**

   - For **Bash**:
     ```bash
     nano ~/.bash_profile
     ```
   - For **Zsh** (the default on modern macOS):
     ```bash
     nano ~/.zshrc
     ```

2. **Add (or update) the following lines**—adjust the SDK path as needed:
   ```bash
   # Configure Android SDK environment variable
   export ANDROID_HOME=$HOME/Library/Android/sdk
   export PATH=$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin:$ANDROID_HOME/platform-tools
   ```

3. **Save the file** and reload your shell:
   ```bash
   source ~/.bash_profile   # or source ~/.zshrc
   ```

4. **Verify the settings:**
   ```bash
   echo $ANDROID_HOME
   echo $PATH
   ```

### On Windows

1. **Open Environment Variables:**
   - Right-click **This PC** (or **My Computer**) and select **Properties**.
   - Click on **Advanced System Settings** and then the **Environment Variables** button.

2. **Set ANDROID_HOME:**
   - Under *User Variables* (or *System Variables*), click **New...**
   - Variable name: `ANDROID_HOME`
   - Variable value: The path to your Android SDK (typically:  
     `C:\Users\<YourUserName>\AppData\Local\Android\Sdk`)

3. **Update the PATH:**
   - Edit the `Path` variable and add:
     - `%ANDROID_HOME%\platform-tools`
     - `%ANDROID_HOME%\tools`
     - (Optionally) `%ANDROID_HOME%\tools\bin`

4. **Apply changes** and verify in a new Command Prompt:
   ```cmd
   echo %ANDROID_HOME%
   ```

---

## Step 1: Install Appium

Install Appium globally with npm:
```bash
npm install -g appium
```
Verify the installation:
```bash
appium -v
```

---

## Step 2: Install the UiAutomator2 Driver

Install the UiAutomator2 driver using Appium’s CLI:
```bash
appium driver install uiautomator2
```

## Step 3: Run the Appium Server

Launch the Appium server with the Inspector plugin enabled, CORS allowed, and with the insecure `adb_shell` enabled:
```bash
appium --use-plugins=inspector --allow-cors --allow-insecure=adb_shell
```
- **--use-plugins=inspector**: Loads the Appium Inspector plugin.
- **--allow-cors**: Allows cross-origin requests.
- **--allow-insecure=adb_shell**: Permits shell commands via adb (use with caution).

---

## Step 4: Set Up an Android Emulator with Android Studio(Skip if you have a Physical Device)

1. **Launch Android Studio**.

2. **Open the AVD Manager:**
   - In the menu, select **Tools** → **AVD Manager**.

3. **Create a New Virtual Device:**
   - Click **Create Virtual Device**.
   - Choose a hardware profile (e.g., Pixel 4) and click **Next**.
   - Select a system image. Download the desired image if necessary.
   - Click **Next**, adjust AVD settings if needed, then click **Finish**.

4. **Run the Emulator:**
   - In the AVD Manager, click the **Play** button (triangle icon) next to your device.

5. **Verify the Emulator is Running:**
   - You should now be able to deploy and test mobile applications on the emulator.

---
## If you prefer to test on a real device, follow these steps:

1. **Enable Developer Options on Your Android Device:**
   - Open **Settings** → **About Phone**.
   - Tap **Build Number** about 7 times until you see a message that Developer Options are enabled.
   - Return to **Settings** and enter **Developer Options**.

2. **Turn On USB Debugging:**
   - In **Developer Options**, locate and enable **USB Debugging**.
   - You might also want to enable **Install via USB** (if available) to simplify app installations.

3. **Connect Your Device:**
   - Use a USB cable to connect your Android device to your computer.
   - On the device, accept any prompt asking to allow USB debugging or to trust the connected computer.

4. **Verify Connection via adb:**
   - Open a Terminal (or Command Prompt on Windows) and run:
     ```bash
     adb devices
     ```
   - You should see your device’s serial number listed. If not, ensure that your USB drivers (on Windows) or proper permissions (on macOS/Linux) are in place.

5. **Troubleshooting:**
   - **Windows:** Install the appropriate device drivers if your device is not recognized.
   - **macOS/Linux:** If your device is not detected, try disconnecting and reconnecting, and verify that you have granted USB debugging permissions on the device.

---
## Final Notes

- **Environment Variables Persistence:**  
  Make sure your shell configuration file (e.g., `.bash_profile`, `.zshrc`) is updated correctly so that `ANDROID_HOME` and your PATH modifications persist across sessions.



---
