# Iteration 10: Steps 10-11 & Completion Flow
## Integration Guide

**Version:** 1.0  
**Date:** February 2026  
**Status:** Ready for Implementation

---

## Overview

This iteration implements the final steps of the Journey Circle Creator workflow:
- **Step 10:** Link Published Assets (URL input after content download)
- **Step 11:** Repeat Workflow (asset completion grid)
- **Journey Completion:** Validation, celebration, and return to Campaign Builder
- **Campaign Builder Integration:** Success notification and client card badges

---

## Deliverables Summary

| File | Purpose | Location |
|------|---------|----------|
| `class-journey-completion-controller.php` | REST API for completion tracking | `/includes/api/` |
| `class-client-journey-status-controller.php` | REST API for client journey statuses | `/includes/api/` |
| `journey-completion.js` | Step 11 & completion workflow UI | `/admin/js/modules/` |
| `asset-creator-step10.js` | Step 10 URL linking extension | `/admin/js/modules/` |
| `client-manager-journey-extension.js` | Campaign Builder integration | `/admin/js/modules/` |
| `journey-completion.css` | All styling for iteration 10 | `/admin/css/` |

---

## Installation Instructions

### Step 1: Copy PHP Files

Copy the PHP controller files to the includes directory:

```bash
# From plugin root
cp iteration-10/includes/api/class-journey-completion-controller.php \
   includes/api/

cp iteration-10/includes/api/class-client-journey-status-controller.php \
   includes/api/
```

### Step 2: Include PHP Files

Add the following to your main plugin file (`directreach-campaign-builder.php`):

```php
// Journey Circle Completion API
require_once DR_PLUGIN_PATH . 'includes/api/class-journey-completion-controller.php';
require_once DR_PLUGIN_PATH . 'includes/api/class-client-journey-status-controller.php';
```

### Step 3: Copy JavaScript Files

```bash
cp iteration-10/admin/js/modules/journey-completion.js \
   admin/js/modules/

cp iteration-10/admin/js/modules/asset-creator-step10.js \
   admin/js/modules/

cp iteration-10/admin/js/modules/client-manager-journey-extension.js \
   admin/js/modules/
```

### Step 4: Copy CSS Files

```bash
cp iteration-10/admin/css/journey-completion.css \
   admin/css/
```

### Step 5: Enqueue Assets

Add to your asset enqueue function (likely in `class-journey-circle-page.php`):

```php
// Enqueue completion CSS
wp_enqueue_style(
    'dr-journey-completion',
    DR_PLUGIN_URL . 'admin/css/journey-completion.css',
    array(),
    DR_VERSION
);

// Enqueue completion JavaScript
wp_enqueue_script(
    'dr-journey-completion',
    DR_PLUGIN_URL . 'admin/js/modules/journey-completion.js',
    array('jquery'),
    DR_VERSION,
    true
);

wp_enqueue_script(
    'dr-asset-creator-step10',
    DR_PLUGIN_URL . 'admin/js/modules/asset-creator-step10.js',
    array('jquery', 'dr-asset-creator'),
    DR_VERSION,
    true
);
```

For Campaign Builder page:

```php
wp_enqueue_script(
    'dr-client-manager-journey',
    DR_PLUGIN_URL . 'admin/js/modules/client-manager-journey-extension.js',
    array('jquery', 'dr-client-manager'),
    DR_VERSION,
    true
);
```

### Step 6: Integrate with Existing Modules

#### Extend asset-creator.js

Add at the end of your existing `asset-creator.js`:

```javascript
// Extend with Step 10 URL linking
if (typeof extendAssetCreatorWithUrlLinking === 'function') {
    extendAssetCreatorWithUrlLinking(AssetCreator);
}
```

#### Update journey-circle-workflow.js

Add Step 10 and Step 11 to your step definitions:

```javascript
const STEPS = {
    // ... existing steps 1-9
    10: {
        id: 10,
        name: 'Link Published Assets',
        component: 'AssetUrlLinker',
        validation: () => true, // URL linking is optional
    },
    11: {
        id: 11,
        name: 'Repeat & Complete',
        component: 'JourneyCompletion',
        validation: (state) => state.completionStatus?.is_complete === true,
    },
};
```

Add transition handling:

```javascript
// In workflow state machine
handleStepTransition(fromStep, toStep) {
    // ... existing logic
    
    if (fromStep === 9 && toStep === 10) {
        // After download, show URL linking
        this.initUrlLinking();
    }
    
    if (fromStep === 10 && toStep === 11) {
        // After URL linking (or skip), show completion grid
        this.initCompletionGrid();
    }
}

initUrlLinking() {
    const urlLinker = new AssetUrlLinker({
        journeyCircleId: this.journeyCircleId,
        apiBase: this.config.apiBase,
        nonce: this.config.nonce,
    });
    urlLinker.init(this.getStepContainer(10), this.currentAsset);
}

initCompletionGrid() {
    const completion = new JourneyCompletion({
        journeyCircleId: this.journeyCircleId,
        clientId: this.clientId,
        serviceAreaId: this.serviceAreaId,
        serviceAreaName: this.serviceAreaName,
        apiBase: this.config.apiBase,
        nonce: this.config.nonce,
    });
    completion.init(this.getStepContainer(11));
    
    // Handle create content event to loop back to Step 9
    this.getStepContainer(11).addEventListener(
        'journeyCompletion:createContent',
        (e) => {
            this.startAssetCreation(e.detail);
        }
    );
}
```

---

## REST API Endpoints

### Completion Controller Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `PUT` | `/journey-circles/{id}/assets/{asset_id}` | Update asset with published URL |
| `PUT` | `/journey-circles/{id}/problems/{problem_id}/asset-urls` | Update problem asset URLs |
| `PUT` | `/journey-circles/{id}/solutions/{solution_id}/asset-urls` | Update solution asset URLs |
| `GET` | `/journey-circles/{id}/completion-status` | Get completion progress |
| `PUT` | `/journey-circles/{id}/complete` | Mark journey as complete |
| `GET` | `/journey-circles/{id}/assets` | Get all assets for journey |

### Client Status Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/clients/journey-statuses?client_ids=1,2,3` | Get journey statuses for clients |

### Example API Calls

**Update Asset URL:**
```javascript
await fetch(`/wp-json/directreach/v2/journey-circles/123/assets/456`, {
    method: 'PUT',
    headers: {
        'Content-Type': 'application/json',
        'X-WP-Nonce': nonce,
    },
    body: JSON.stringify({
        url: 'https://example.com/published-article'
    }),
});
```

**Get Completion Status:**
```javascript
const response = await fetch(
    `/wp-json/directreach/v2/journey-circles/123/completion-status`,
    {
        headers: { 'X-WP-Nonce': nonce },
    }
);
const status = await response.json();
// status = {
//     journey_circle_id: 123,
//     is_complete: false,
//     completion_percentage: 70,
//     problems: { total: 5, completed: 4, items: [...] },
//     solutions: { total: 5, completed: 3, items: [...] },
//     assets: { total: 7, items: [...] }
// }
```

**Mark Complete:**
```javascript
const response = await fetch(
    `/wp-json/directreach/v2/journey-circles/123/complete`,
    {
        method: 'PUT',
        headers: { 'X-WP-Nonce': nonce },
    }
);
// Returns completion data for sessionStorage
```

---

## Event Flow

### Step 10 → Step 11 Flow

```
Step 9: Content Downloaded
    ↓
AssetCreator.handleDownloadComplete()
    ↓
AssetCreator.showUrlLinkingPhase()
    ↓
AssetUrlLinker.init()
    ↓
[User enters URL or clicks Skip]
    ↓
'assetUrlLinker:urlLinked' or 'assetUrlLinker:urlSkipped'
    ↓
'assetUrlLinker:continueToNext'
    ↓
AssetCreator.transitionToStep11()
    ↓
'proceedToStep11' event
    ↓
JourneyCompletion.init()
```

### Completion Flow

```
JourneyCompletion: User clicks "Complete Journey"
    ↓
handleCompleteJourney()
    ↓
PUT /journey-circles/{id}/complete
    ↓
storeCompletionData() → sessionStorage
    ↓
render() with celebration UI
    ↓
[User clicks "Return to Campaign Builder"]
    ↓
navigateToCampaignBuilder()
    ↓
window.location → Campaign Builder with ?journey_success=1
```

### Campaign Builder Return Flow

```
Campaign Builder loads
    ↓
JourneyIntegration.init()
    ↓
checkJourneyCompletion()
    ↓
Read sessionStorage 'dr_journey_completed'
    ↓
showSuccessBanner()
    ↓
updateClientCard() → Add badge
    ↓
Clear sessionStorage
    ↓
cleanupUrl() → Remove query param
```

---

## SessionStorage Data Structure

When journey completes, this data is stored:

```javascript
{
    success: true,
    timestamp: "2026-02-12T10:30:00.000Z",
    clientId: 123,
    clientName: "Acme Corp",
    serviceAreaId: 456,
    serviceAreaName: "Cloud Migration",
    circleComplete: true,
    problemCount: 5,
    solutionCount: 5,
    assetCount: 10
}
```

---

## Testing Checklist

### Step 10: URL Linking

- [ ] After downloading content from Step 9, URL linking UI appears
- [ ] URL input validates format (requires http:// or https://)
- [ ] Invalid URLs show error message
- [ ] Valid URLs show success checkmark
- [ ] Submitting URL updates `dr_journey_assets` table with URL
- [ ] Asset status changes to "published"
- [ ] URL is also synced to problem/solution `asset_urls` JSON
- [ ] Skip button works and proceeds to Step 11
- [ ] Success message shows after linking
- [ ] "Continue" button proceeds to Step 11

### Step 11: Completion Grid

- [ ] Grid loads and shows all 5 problems
- [ ] Grid loads and shows all 5 solutions
- [ ] Complete items show green checkmark
- [ ] Incomplete items show gray circle
- [ ] Primary problem has special badge
- [ ] Selecting an item highlights it
- [ ] "Create Content" button enables when item selected
- [ ] Clicking "Create Content" navigates back to Step 9
- [ ] Progress bar shows correct percentage
- [ ] Stats show correct completed counts
- [ ] Asset URLs display as external links

### Journey Completion

- [ ] "Complete Journey" button appears when all items have assets
- [ ] Button is disabled if requirements not met
- [ ] Clicking "Complete" calls API to update status
- [ ] API validates completion requirements
- [ ] Journey circle status becomes "complete"
- [ ] Celebration UI displays with stats
- [ ] "Return to Campaign Builder" button works
- [ ] SessionStorage is populated correctly

### Campaign Builder Integration

- [ ] Success banner shows on return
- [ ] Banner displays correct service area name
- [ ] Banner displays correct stats
- [ ] Banner can be dismissed
- [ ] Banner auto-dismisses after 10 seconds
- [ ] Client card gets journey badge
- [ ] Badge shows "Journey Complete" for complete journeys
- [ ] URL parameter is cleaned up
- [ ] SessionStorage is cleared after display

### API Endpoints

- [ ] `PUT /journey-circles/{id}/assets/{asset_id}` - Updates asset URL
- [ ] `PUT /journey-circles/{id}/problems/{pid}/asset-urls` - Updates problem
- [ ] `PUT /journey-circles/{id}/solutions/{sid}/asset-urls` - Updates solution
- [ ] `GET /journey-circles/{id}/completion-status` - Returns correct data
- [ ] `PUT /journey-circles/{id}/complete` - Marks complete only when valid
- [ ] `GET /clients/journey-statuses` - Returns statuses for multiple clients
- [ ] All endpoints require nonce verification
- [ ] All endpoints require `manage_campaigns` capability
- [ ] Invalid IDs return 404
- [ ] Validation errors return 400

### Responsive Design

- [ ] URL linking form works on mobile
- [ ] Completion grid is single column on mobile
- [ ] Buttons stack vertically on mobile
- [ ] Progress bar is readable on small screens
- [ ] Celebration UI is properly sized on mobile

### Error Handling

- [ ] Network errors show user-friendly messages
- [ ] API errors are logged to console
- [ ] Retry button works on error states
- [ ] Loading states show during API calls
- [ ] Button disables during submission

### Cross-Browser

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

---

## Troubleshooting

### "Failed to load completion status"

1. Check browser console for specific error
2. Verify journey circle ID is valid
3. Check REST API authentication (nonce)
4. Verify user has `manage_campaigns` capability

### Journey badge not showing on client card

1. Check if `client_ids` parameter is being sent correctly
2. Verify service area exists for the client
3. Check if journey circle has been created
4. Inspect network tab for API response

### URL validation always fails

1. Ensure URL includes protocol (http:// or https://)
2. Check for leading/trailing whitespace
3. Verify hostname has a TLD (e.g., .com)

### Completion data not persisting

1. Check if sessionStorage is available (not private browsing)
2. Verify data is being written with correct key
3. Check for JavaScript errors before storage write

---

## Architecture Notes

### Database Updates

No database schema changes required. This iteration uses existing columns:

- `dr_journey_assets.url` - Stores published URL
- `dr_journey_assets.status` - Updated to "published"
- `dr_journey_problems.asset_urls` - JSON array of URLs
- `dr_journey_solutions.asset_urls` - JSON array of URLs
- `dr_journey_circles.status` - Updated to "complete"

### State Management

- Completion status is always fetched from database (no caching)
- Local selection state is managed in JavaScript
- SessionStorage used only for cross-page communication
- LocalStorage continues to store workflow progress

### Security

- All endpoints verify WordPress nonce
- All endpoints check `manage_campaigns` capability
- URLs are sanitized with `esc_url_raw()`
- Output is escaped in templates
- Prepared statements used for all queries

---

## Future Considerations

1. **Offline Support:** Consider IndexedDB for offline-capable asset management
2. **Bulk Operations:** Add ability to link multiple URLs at once
3. **URL Validation:** Add server-side URL accessibility check
4. **Analytics:** Track completion rates and time-to-complete
5. **Notifications:** Email notification when journey completes

---

**End of Integration Guide**
