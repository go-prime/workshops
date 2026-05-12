# Playwright Workshop

## Introduction

 
Modern web applications can be highly dynamic, stateful, and user-driven. Modern applications are heavily reliant on asynchronous rendering, API driven updates, client-side routing (**CSR**) and permission-aware interfaces. These features make UI behaviors harder to test using traditional automation approaches


Playwright addresses these challenges with a deterministic, browser-native automation model that enables reliable end-to-end testing across Chromium, Firefox, and WebKit.

## Why UI Testing Is Important

 Some of our systems, especially our ERP systems are workflow heavy, have extreme role sensitivity (permissions often affect UI Behavior) and can be very state dependent (state transitions affect visibility. Meaning, systems will be highly responsive to document state). For example a document in 'Draft' state will render "Save" when a change is detected as well as "Submit" when changes are synced and will also hide edit options when Document is submitted and so forth. Back-end testing cannot validate this dynamic form interactions, client side validation and desired User Experience. This is the gap bridged by tools like Playwright.

## Drawbacks of Traditional UI Testing

 1. **Shaky Selectors**. - Tests break when UIs have minor structural and styling updates.
 2. **Timing**. - Test can become fragile due to asynchronous rendering
 3. **Manual Waits**. - Slower unreliable scripts.
 4. **Poor Debugging.** - Traditional approaches provided limited visibility into causes of failures. Questions as to which selector failed, if the page loaded correctly, what network requests occurred, what the browser visually displayed - is not immediately determined.

## Playwright Core Features

 1. **Auto-Waiting**. - No need for sleep function call or manual delays. Playwright waits for elements to become actionable, intelligently.
 2. **Context Isolation**. - Every test runs in a fresh and clean environment.
 3. **Rich/Powerful Selectors**. - Playwright supports text selectors, role based selectors, label selectors in addition to the shaky CSS Selectors and **XPath** queries. 
 4. **Network Interception**. - Mock APIs or observe backend calls. Playwright can observe, modify or mock requests made by the browser. This is useful for debugging backend communication, simulating API failures, testing offline behavior, etc.
 ```javascript
 // This will intercept all requests matching this path
 await page.route('**/api/method/**', route => {
  console.log(route.request().url());
  route.continue();
});
 ```
 6. 

### Comparison v Selenium and Cypress


|  | Playwright | Selenium | Cypress |
| :------: | :------: | :------: | :------: |
| **Owner**      | Microsoft     | Open Source       | Cypress.io     |
|    **Languages**   | JS, TS, Python, Java, .NET     | Java, Python, JS, C#, Ruby, PHP      | Ruby, PHP,JavaScript, Typescript    |
|**Speed**|Fastest|Slower (Overhead)|Fast (Slow startup)|
|**Mobile Testing**|Emulation (Native)|Via Appium (External)| No|
|**Learning Curve**|Moderate|Steep|Easy (for JS developers)|
|**Community**|Rapidly Growing|Largest / Mature|Large / Developer-focused|
|**Strengths**|Speed, Trace Viewer, and multi-browser support.|Language flexibility and industry-wide support.|Easy setup; fast feedback for JS devs|
|**Weaknesses**|Newer ecosystem; fewer 3rd party plugins|Harder to maintain; prone to flakiness.|Restricted to JS/TS; limited browser control.|

## Setting up
Ensure node is installed.
```bash
mkdir playwright-project
cd playwright-project
npm init playwright@latest
```
The following prompts will appear:
- Typescript or JavaScript (default: Typescript)
- Tests folder name (default: `tests`, or `e2e` if `tests` already exists)
- Add a GitHub Actions workflow (recommended for CI) - Playwright can be used to automatically run tests within GitHub Actions. 
Refere to `sample_action.yaml`

```bash 
Developer Pushes Code
        ↓
GitHub Action Runs
        ↓
Playwright Executes Tests
        ↓
Results Attached to Build
```



- Install Playwright browsers (default: yes) - Will install browser engines for Chromium, Firefox and WebKit.

### Project Structure
```bash
tests/
  login.spec.js
  quotation-order.spec.js
playwright.config.js
```
### Running the Tests
#### Running all tests.
```bash
npx playwright test
```
#### Run specific test.
```bash
npx playwright test tests/login.spec.js
```
#### Run specific test by name
```bash
npx playwright test -g "login page"
```
**Run tests in headed mode**. I.e running tests while s prompting the opening of a browser. Playwright runs headless by default. Headed is useful for demonstration purposes, watching live execution of workflows, debugging UI issues visually.
```bash
npx playwright test --headed
```
#### Run tests in debug mode.


 1. Runs while opening Playwright Inspector.
 2. Slows execution
 3. Allows step by step inspection.

```bash
npx playwright test --debug
```
#### Run in specific browsers
```bash
npx playwright test --project=chromium
```
Flags
```bash
--project=firefox
--project=webkit
```
#### Run using VSCode Extension
https://playwright.dev/docs/getting-started-vscode

### Configuration
All configs will be centrally controlled within the file
```bash
playwright.config.js
```
This will control the following

 1. Browser behavior
 2. Timeouts (default: 30000ms)
 3. Reporting
 4. Trace collection
 5. Error capture by video or image.

 #### Authentication Persistence
 `storageState` allows you to save authentication session over several tests. 

 ```javascript
 // Save the signed-in state to a file
  await page.context().storageState({ path: 'playwright/.auth/user.json' });
 ```

```bash
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  timeout: 30000,

  use: {
    baseURL: 'http://localhost:8000',

    headless: true,

    screenshot: 'only-on-failure',

    video: 'retain-on-failure',

    trace: 'retain-on-failure'
  }
});
```

### Basic Login Test
```javascript
const { test, expect } = require('@playwright/test');

test('login page', async ({ page }) => {
  await page.goto('http://localhost:8000/login');

  await page.fill('#login_email', 'Administrator');
  await page.fill('#login_password', 'admin123');

  await page.click('button:has-text("Login")');

  await expect(page).toHaveURL(/dashboard/);
});
```
### Dynamic Form Interaction
```javascript 
test('Create Sales Order', async ({ page }) => {
  await page.goto('/app/sales-order/new');

  await page.fill('[data-fieldname="customer"] input', 'Test Customer');
  await page.click('[data-fieldname="customer"] .awesomplete li');

  await page.click('button:has-text("Add Row")');

  await page.fill('[data-fieldname="item_code"] input', 'Test Item');
  await page.keyboard.press('Enter');

  await page.click('button:has-text("Save")');

  await expect(page.locator('.indicator')).toHaveText('Draft');
});
```

### Workflow Transition Testing
```javascript
test('Submit Sales Order', async ({ page }) => {
  await page.click('button:has-text("Submit")');
  await expect(page.locator('.indicator')).toHaveText('Submitted');
});
```

### Asynchronous UI Handling
```javascript
// resolves as the element appears in DOM
await page.waitForSelector('.form-dashboard');
```
Or even better
```javascript
// while waitForSelector resolves when element exist in DOM
// it might not be visible or interactable. 
// toBeVisible automatically waits (retries) until the element meets the visibility criteria or the timeout is reached
await expect(page.locator('.form-dashboard')).toBeVisible();
```
 
### Role Based UI Testing
```javascript
test('Sales User cannot submit', async ({ page }) => {
  // login as limited user

  await page.goto('/app/sales-order/new');

  await expect(page.locator('button:has-text("Submit")')).toBeHidden();
});
```

### Network Interception
```javascript 
await page.route('**/api/method/**', route => {
  console.log(route.request().url());
  route.continue();
});
// Note you can return a response for what you want to test
// Use route.abort() to mimic network cut out
// Use route.fulfill()
```

### Take A Screenshot
```javascript
await page.screenshot({ path: 'debug.png' });
```

### Failed Tests and Test Result Logging
On every failed test, informative debugging artifacts are collected. These will contain errors such as:

 1. Error stack-traces
 2. Page Snapshots
 3. Screen shots and Video Capture
 4. Trace files
 5. Network activity
 6. DOM snapshots

The results of failed tests will be stored in the folder named. `test-results/`

```bash
npx playwright test --trace on
```
Then
```bash
npx playwright show-trace trace.zip

```
### Viewing HTML Report
BASH
```bash
npx playwright test --reporter=html; npx playwright show-report
```
Powershell
```powershell
npx playwright test --reporter=html; npx playwright show-report
```
Will show report at `http://localhost:9323/` containing:

-   Passed and Failed tests
-   Execution time
-   Attached screenshots (if configured)
-   Trace links
-   Error Stack-Traces

## Playwright MCP (Model Context Protocol).
Playwright has an official MCP tool that allows your agents to carry out specific tasks on your UI. It allows agents to:

- Generate and execute test scripts based on exploration.
- Debug failing tests by inspecting the DOM and logging errors
- Self healing by dynamically adjusting selectors on UI changes. Agents can iterate over failing selectors dynamically adjusting based on analyzing and inspecting the DOM.

User → AI Agent → MCP → Playwright → Browser → Application UI. You can set up by installing the tool on **Docker Desktop** and configuring your client to access it. On **Claude Code** add the following to the mcp servers block on config file as follows.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest"
      ]
    }
  }
}
```

### Use Cases

 1. Generate scripts based on UI exploration.
 2. Debugging - Inspect DOM, network logs, take screenshots upon UI Failure
 3. Self healing - Adjust selectors dynamically when UI changes.
 When UI change breaks a selector a self healing agent can reinspect the DOM, identify the element and update the selector automatically.

```bash
// pseudo-flow
AI → "Find login button"
MCP → DOM query
Playwright → click element
```
## Best Practices
### Suitable Selectors
```javascript
// Use
getByRole()
getByText()
// instead of
.div > span:nth-child(2)
```
### Test Data
Use seeded tested test data in lieu of production
### Test Isolation
Each test needs to be independent of other tests. I.e not dependent on previous tests
### Avoid Hard Waits
```javascript
// Dont Do This
await page.waitForTimeout(3000);

// Do this
await expect(locator).toBeVisible();
```

## Additional Information
- https://playwright.dev/docs/intro
- https://playwright.dev/python/docs/api/class-route
- https://www.browserstack.com/guide/playwright-vs-selenium
- https://testomat.io/blog/playwright-vs-selenium-vs-cypress-a-detailed-comparison/
- https://playwright.dev/docs/pom

## Terminology
- **CSR** - Methodology used in Single Page Applications where JavaScript in the browser handles navigation, rendering new views without full page reloads
- **APPIUM** - open-project, cross-platform test automation framework designed for native, hybrid, and mobile web apps.
- **SELECTOR** - A selector is the mechanism used to identify an element on the page.
- **XPATH** - A query language used to navigate and locate elements in XML or HTML documents.
- **CSS SELECTORS** - They are patterns used to select and style HTML elements based on their attributes, classes, IDs, or hierarchy.



