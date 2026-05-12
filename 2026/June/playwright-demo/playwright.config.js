const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  timeout: 30000,

  name: 'webkit',
  use: {

    // headless: false,
    // storageState: 'playwright/.auth/user.json',

    screenshot: 'only-on-failure',

    video: 'retain-on-failure',

    trace: 'retain-on-failure'
  },
  // dependencies: ['setup'],
});