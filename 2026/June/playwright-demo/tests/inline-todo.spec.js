const { test, expect } = require('@playwright/test');

test('Create Todo from quick entry popup', async ({ page }) => {
    //   log in
    await page.goto('http://localhost:8000/#login');

    await page.fill('#login_email', 'Administrator');
    await page.fill('#login_password', 'admin');

    await page.click('button:has-text("Login")');
    // Wait for login to complete before proceeding
    await page.waitForURL('**/desk', { timeout: 15000 });

    await page.goto('http://localhost:8000/desk#List/ToDo/List');

    // Wait for the list page to be ready
    await page.waitForSelector('.page-head', { timeout: 10000 });

    // Dismiss any open overlays (datepickers, dropdowns)
    await page.keyboard.press('Escape');

    // Target the specific Add button, not the dropdown toggle
    await page.click('button.primary-action');

   // Target the Quill editor inside the description field
    await page.locator('div[data-fieldname="description"] .ql-editor').click();
    await page.locator('div[data-fieldname="description"] .ql-editor').fill('Prepare workshop notes');

    await page.click('button:has-text("Save")');

    // Wait for the modal to close and the list to refresh
    await page.waitForSelector('.new-todo-quick-entry', { state: 'hidden', timeout: 10000 });

    // Scope assertion to data rows only, excluding the header
    await expect(
    page.getByRole('link', { name: 'Prepare workshop notes' })
    ).toBeVisible();
});