const { test, expect } = require('@playwright/test');

test('login to ERPNext', async ({ page }) => {
  await page.goto('http://localhost:8000/#login');

  await page.fill('#login_email', 'Administrator');
  await page.fill('#login_password', 'admin');

  await page.click('button:has-text("Login")');

  await expect(page).toHaveURL('http://localhost:8000/desk');
});