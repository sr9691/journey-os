# Journey Circle - Extension File Merge Guide
**Generated:** February 13, 2026

---

## Overview

Your merged plugin structure is in `/journey-circle-final/`. Most files (33 of 34) have been directly copied. This guide covers the **6 extension files** that require manual integration.

---

## ✅ Already Complete

The following are already in your final structure and need no further merging:

- **`journey-circle-renderer.js`** (Iteration 7, 942 lines) - **Complete canvas renderer**
  - Already includes all problem, solution, and offer ring visualization
  - The Iteration 5 and 6 renderer extensions were superseded by this version
  - No merge needed

---

## 📋 Extension Files Requiring Manual Merge

All extension files are in `/journey-circle-final/merge-reference/`

### 1. `workflow-updates-iteration5.js` → `journey-circle-workflow.js`

**What it adds:** Steps 4-6 handling (Industry, Primary Problem, Problem Titles)

**Merge Instructions:**

1. **Add to Constructor** (after line ~28):
```javascript
// Initialize Problem/Solution Manager
this.problemSolutionManager = new ProblemSolutionManager(this, {
    apiBase: this.config.apiBase,
    nonce: this.config.nonce
});
```

2. **Update `renderCurrentStep()` method** - Add cases 4, 5, 6:
```javascript
case 4: // Industry Selection
    this.problemSolutionManager.renderIndustrySelection(container);
    break;
case 5: // Primary Problem
    this.problemSolutionManager.renderPrimaryProblem(container);
    break;
case 6: // Problem Titles
    this.problemSolutionManager.renderProblemTitles(container);
    break;
```

3. **Update `validateStep()` method** - Add validation for steps 4, 5, 6

4. **Full reference:** See `merge-reference/workflow-updates-iteration5.js`

---

### 2. `asset-creator-step10.js` → Works alongside `asset-creator.js`

**What it adds:** `AssetUrlLinker` class for Step 10 (linking published URLs)

**Merge Instructions:**

This is a **companion class**, not a replacement. Two options:

**Option A:** Keep as separate file (Recommended)
- Copy `asset-creator-step10.js` to `/admin/js/modules/`
- Import/load alongside `asset-creator.js`
- Use `AssetUrlLinker` class when entering Step 10

**Option B:** Append to `asset-creator.js`
- Add the `AssetUrlLinker` class at the end of `asset-creator.js`
- Export both classes

---

### 3. `class-ai-content-controller-extension.php` → `class-ai-content-controller.php`

**What it adds:** 
- REST routes for outline/content generation
- Asset CRUD endpoints
- Approval and publish endpoints

**Merge Instructions:**

1. **Add Route Registrations to `register_routes()` method:**
   - `/ai/generate-outline` (POST)
   - `/ai/revise-outline` (POST)
   - `/ai/generate-content` (POST)
   - `/ai/revise-content` (POST)
   - `/journey-circles/{id}/assets` (GET, POST)
   - `/journey-circles/{id}/assets/{asset_id}` (GET, PUT, DELETE)
   - `/journey-circles/{id}/assets/{asset_id}/approve` (POST)
   - `/journey-circles/{id}/assets/{asset_id}/publish` (POST)

2. **Add Callback Methods** (insert before class closing brace):
   - `generate_outline($request)`
   - `revise_outline($request)`
   - `generate_content($request)`
   - `revise_content($request)`
   - `get_assets($request)`
   - `get_asset($request)`
   - `create_asset($request)`
   - `update_asset($request)`
   - `delete_asset($request)`
   - `approve_asset($request)`
   - `publish_asset($request)`

3. **Add Helper Methods:**
   - `get_outline_args()`
   - `get_create_asset_args()`
   - `get_update_asset_args()`
   - `format_asset_for_response($asset)`

4. **Full reference:** See `merge-reference/class-ai-content-controller-extension.php`

---

### 4. `class-ai-content-generator-extension.php` → `class-ai-content-generator.php`

**What it adds:**
- Outline generation methods
- Content generation methods
- Revision handling
- Asset management helpers

**Merge Instructions:**

1. **Add Public Methods:**
   - `generate_outline($args)` - Main outline generation
   - `revise_outline($args)` - Revise based on feedback
   - `generate_content($args)` - Full content generation
   - `revise_content($args)` - Revise content based on feedback
   - `approve_asset($asset_id)` - Mark asset as approved
   - `publish_asset($asset_id, $url)` - Link published URL

2. **Add Private Helper Methods:**
   - `build_outline_prompt($args)`
   - `parse_outline_response($response, $args)`
   - `format_outline_as_text($data)`
   - `build_content_prompt($outline, $asset, $context)`
   - `clean_generated_content($content)`
   - `get_outline_cache_key($args)`
   - `clear_outline_cache($asset_id)`
   - `summarize_brain_content($brain_content)`
   - `get_content_context($asset)`
   - `create_or_update_asset($args, $outline, $title)`
   - `update_asset_outline($asset_id, $outline, $title)`
   - `update_asset_content($asset_id, $content, $status)`
   - `get_asset($asset_id)`
   - `extract_json_from_response($response)`

3. **Full reference:** See `merge-reference/class-ai-content-generator-extension.php`

---

### 5. `renderer-updates-iteration5.js` - **SKIP**

This file has been **superseded** by the Iteration 7 renderer. The Iteration 7 version already includes all problem ring functionality with better architecture. **No merge needed.**

---

### 6. `journey-circle-renderer-ext.js` - **SKIP**

This file has been **superseded** by the Iteration 7 renderer. The Iteration 7 version already includes solution ring and offer center functionality. **No merge needed.**

---

## 🔧 Quick Merge Script

For the PHP files, you can use this approach:

```bash
# Create backup
cp class-ai-content-controller.php class-ai-content-controller.php.backup
cp class-ai-content-generator.php class-ai-content-generator.php.backup

# The extension files have clear section markers.
# Find "// CALLBACK METHODS" in the extension and copy everything
# from there to the end of the extension file.
# Insert it before the closing brace of your base class.
```

---

## 📁 Final Directory Structure

After merging, your structure should be:

```
journey-circle-final/
├── admin/
│   ├── css/
│   │   ├── journey-circle.css              (base styles)
│   │   ├── journey-circle-steps456.css     (steps 4-6)
│   │   ├── journey-circle-steps78.css      (steps 7-8)
│   │   ├── journey-circle-canvas.css       (canvas)
│   │   ├── journey-circle-ai.css           (AI features)
│   │   ├── journey-circle-asset.css        (asset creation)
│   │   └── journey-completion.css          (completion flow)
│   │
│   ├── js/modules/
│   │   ├── journey-circle-workflow.js      (+ merged steps 4-6)
│   │   ├── journey-circle-renderer.js      (complete - no merge needed)
│   │   ├── brain-content-manager.js
│   │   ├── service-area-manager.js
│   │   ├── problem-solution-manager.js
│   │   ├── solution-offer-manager.js
│   │   ├── ai-title-manager.js
│   │   ├── asset-creator.js                (+ merged step 10)
│   │   ├── journey-completion.js
│   │   └── client-manager-journey-extension.js
│   │
│   └── views/journey-circle/
│       ├── journey-circle-creator.php
│       └── step-9-template-snippet.php
│
├── includes/
│   ├── journey-circle/
│   │   ├── class-journey-circle-page.php
│   │   └── class-ai-content-generator.php  (+ merged extension)
│   │
│   └── api/
│       ├── class-industries-controller.php
│       ├── class-journey-problems-controller.php
│       ├── class-journey-solutions-controller.php
│       ├── class-ai-content-controller.php (+ merged extension)
│       ├── class-journey-completion-controller.php
│       └── class-client-journey-status-controller.php
│
├── docs/
│   ├── ITERATION_4_DOCUMENTATION.md
│   ├── MODIFICATIONS_TO_EXISTING_FILES.md
│   ├── TESTING_CHECKLIST.md
│   └── FINAL_INTEGRATION_GUIDE.md
│
└── merge-reference/                        (delete after merging)
    ├── workflow-updates-iteration5.js
    ├── asset-creator-step10.js
    ├── class-ai-content-controller-extension.php
    └── class-ai-content-generator-extension.php
```

---

## ✅ Verification Checklist

After merging, verify:

- [ ] All 11 workflow steps render correctly
- [ ] Industry selection (Step 4) works
- [ ] Problem selection (Steps 5-6) works
- [ ] Canvas renders all three rings
- [ ] AI title generation works
- [ ] AI content generation works
- [ ] Asset approval flow works
- [ ] URL linking (Step 10) works
- [ ] Journey completion badge shows on client card

---

## Need Help?

The extension files in `merge-reference/` contain complete, working code with clear section markers. Each method is documented with PHPDoc/JSDoc comments explaining its purpose and parameters.
