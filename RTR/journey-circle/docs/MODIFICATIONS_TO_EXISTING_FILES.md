# Modifications to Existing Files
## Journey Circle Creator - Iteration 4

These are the **ONLY 2 existing files** that need modifications to integrate Journey Circle Creator.

---

## 1. `directreach-campaign-builder.php`

**Location**: Root of plugin directory  
**Action**: Add one line to load the Journey Circle page class

### Code to Add

Find where you load other includes (probably near the top after the plugin header), and add:

```php
// Journey Circle Creator
require_once plugin_dir_path(__FILE__) . 'includes/journey-circle/class-journey-circle-page.php';
```

### Full Context Example

```php
<?php
/**
 * Plugin Name: DirectReach Campaign Builder
 * ... other headers ...
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Load core classes
require_once plugin_dir_path(__FILE__) . 'includes/class-campaign-builder.php';
require_once plugin_dir_path(__FILE__) . 'includes/class-client-manager.php';
// ... other includes ...

// ADD THIS LINE:
require_once plugin_dir_path(__FILE__) . 'includes/journey-circle/class-journey-circle-page.php';
```

---

## 2. `admin/js/modules/client-manager.js`

**Location**: `/admin/js/modules/client-manager.js`  
**Action**: Add Journey Circle button to client cards

### Modification #1: Add Button HTML

Find the `renderClientCard()` method (probably around line 226) where it renders the action buttons.

**Find this section:**
```javascript
<div class="client-card-actions">
    <button class="btn btn-sm btn-secondary configure-client-btn">
        <i class="fas fa-cog"></i> Configure
    </button>
    <button class="btn btn-sm btn-primary run-nightly-job-btn">
        <i class="fas fa-play"></i> Run Nightly Job
    </button>
</div>
```

**Add this button:**
```javascript
<div class="client-card-actions">
    <button class="btn btn-sm btn-secondary configure-client-btn">
        <i class="fas fa-cog"></i> Configure
    </button>
    <button class="btn btn-sm btn-primary run-nightly-job-btn">
        <i class="fas fa-play"></i> Run Nightly Job
    </button>
    <!-- ADD THIS BUTTON: -->
    <button class="btn btn-sm btn-info journey-circle-btn" data-client-id="${client.id}">
        <i class="fas fa-circle-notch"></i> Journey Circle
    </button>
</div>
```

### Modification #2: Add Click Handler

Find the event delegation section (probably around line 113) where click events are handled.

**Find this section:**
```javascript
// Handle button clicks
$('.client-list').on('click', '.configure-client-btn', function(e) {
    e.preventDefault();
    // ... configure logic ...
});

$('.client-list').on('click', '.run-nightly-job-btn', function(e) {
    e.preventDefault();
    // ... run job logic ...
});
```

**Add this handler:**
```javascript
// Handle button clicks
$('.client-list').on('click', '.configure-client-btn', function(e) {
    e.preventDefault();
    // ... configure logic ...
});

$('.client-list').on('click', '.run-nightly-job-btn', function(e) {
    e.preventDefault();
    // ... run job logic ...
});

// ADD THIS HANDLER:
$('.client-list').on('click', '.journey-circle-btn', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const clientId = $(this).data('client-id');
    if (!clientId) {
        console.error('No client ID found');
        return;
    }
    
    // Navigate to Journey Circle Creator
    window.location.href = `admin.php?page=dr-journey-circle&client_id=${clientId}`;
});
```

---

## Alternative: If You Don't Have client-manager.js Yet

If `client-manager.js` doesn't exist yet, you can add the button directly in your client card HTML template instead.

**Find your client card template** (probably in PHP) and add:

```php
<div class="client-card-actions">
    <button class="btn btn-sm btn-secondary configure-client-btn">
        <i class="fas fa-cog"></i> Configure
    </button>
    <button class="btn btn-sm btn-primary run-nightly-job-btn">
        <i class="fas fa-play"></i> Run Nightly Job
    </button>
    <a href="<?php echo admin_url('admin.php?page=dr-journey-circle&client_id=' . $client->id); ?>" 
       class="btn btn-sm btn-info">
        <i class="fas fa-circle-notch"></i> Journey Circle
    </a>
</div>
```

---

## Summary

**That's it!** Only 2 small modifications needed:

1. ✅ Add 1 line to `directreach-campaign-builder.php` (loads page class)
2. ✅ Add button + handler to `client-manager.js` (navigation to Journey Circle)

All other files are completely new and standalone.

---

## Verification Checklist

After making these changes:

- [ ] Journey Circle page class loaded (check for PHP errors)
- [ ] "Journey Circle" button appears on client cards
- [ ] Clicking button navigates to Journey Circle Creator
- [ ] Page loads without JavaScript errors
- [ ] Client ID passed correctly in URL

---

## Need Help?

If you encounter issues:

1. **Check browser console** for JavaScript errors
2. **Check PHP error logs** for loading errors
3. **Verify file paths** match your plugin structure
4. **Test with one client** first before rolling out

---

**Last Updated**: February 11, 2026
