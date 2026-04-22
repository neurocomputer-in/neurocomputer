#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Example: Building Infinity Mobile App...${NC}"

# Navigate to android directory
cd infinity_mobile/android

# Make gradlew executable just in case
chmod +x gradlew

# Build Release APK
echo -e "${GREEN}Running: ./gradlew assembleRelease${NC}"
./gradlew assembleRelease

APK_PATH="app/build/outputs/apk/release/app-release.apk"

if [ -f "$APK_PATH" ]; then
    echo -e "${GREEN}Build successful! APK at: $APK_PATH${NC}"
    
    # Check for connected devices
    echo -e "${GREEN}Checking for connected Android devices...${NC}"
    adb devices
    
    # Install APK
    echo -e "${GREEN}Installing APK via ADB...${NC}"
    adb install -r "$APK_PATH"
    
    echo -e "${GREEN}Deployment Complete!${NC}"
else
    echo -e "${RED}Build failed: APK not found at $APK_PATH${NC}"
    exit 1
fi
